#!/usr/bin/env python3
"""
GlowBox - camera_test.py
Step-by-step camera check. Prints PASS / WARN / FAIL for each step and saves test pictures.

Run with a strip (or white paper) in the holder and the box closed:
    python3 camera_test.py            # tests the mode set in hardware_config.CAM_MODE
    python3 camera_test.py rgb        # force the fallback (processed colour) mode
    python3 camera_test.py raw        # force raw mode

Paste the full output to whoever is helping you if anything fails.
"""
import os
import sys
import time
import traceback

import numpy as np

import analysis
import hardware_config as cfg
import storage

RESULTS = []


def report(status, step, detail=""):
    RESULTS.append((status, step))
    print(f"[{status:4}] {step}" + (f"\n        {detail}" if detail else ""))


def stats(img):
    return float(img.mean()), float(np.percentile(img, 99)), float(img.max())


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    print("=== GlowBox camera test ===")

    # 1. picamera2 installed?
    try:
        import picamera2
        from picamera2 import Picamera2
        report("PASS", "picamera2 imported", getattr(picamera2, "__version__", ""))
    except Exception as e:
        report("FAIL", "picamera2 not importable", f"{e!r}\n        fix: sudo apt install -y python3-picamera2")
        return

    # 2. camera detected?
    info = Picamera2.global_camera_info()
    if not info:
        report("FAIL", "no camera detected",
               "check ribbon orientation/seating (Pi OFF when re-plugging); run: rpicam-hello --list-cameras")
        return
    models = [c.get("Model") for c in info]
    report("PASS" if any("imx708" in str(m) for m in models) else "WARN", "camera detected", f"models={models}")

    # 3. GPIO for the LEDs
    try:
        from gpiozero import DigitalOutputDevice
        excite = DigitalOutputDevice(cfg.GPIO_EXCITE, active_high=True, initial_value=False)
        report("PASS", f"LED switch on GPIO{cfg.GPIO_EXCITE} ready")
    except Exception as e:
        report("FAIL", "could not open the LED GPIO", repr(e))
        return

    # 4. start camera
    from camera_reader import CameraReader
    try:
        cam = CameraReader(cfg, excite, mode=mode, verbose=True)
    except Exception as e:
        report("FAIL", "camera failed to start", f"{e!r}\n        try: python3 camera_test.py rgb")
        traceback.print_exc()
        excite.off()
        return
    try:
        if cam.fallback_reason:
            report("WARN", "raw mode failed, using rgb mode", cam.fallback_reason)
        else:
            report("PASS", f"camera started in {cam.mode_name} mode",
                   f"full scale={cam.full_scale}" + (f", bayer={cam.bayer}" if cam.bayer else ""))

        # 5. dark frame (LEDs off)
        cam.leds.off()
        dark = cam._grab(cfg.N_DARK_FRAMES)
        dm, d99, dmax = stats(dark)
        report("PASS" if d99 < 0.2 * cam.full_scale else "WARN", "dark frame (LEDs off)",
               f"mean={dm:.1f} p99={d99:.1f} max={dmax:.1f} size={dark.shape[1]}x{dark.shape[0]}"
               + ("" if d99 < 0.2 * cam.full_scale else "  -> light is leaking into the box"))

        # 6. LED sync: frames straight after switching the LEDs on, no flushing
        cam.picam2.capture_request().release()
        seq = []
        try:
            cam.leds.on()
            t0 = time.monotonic()
            for _ in range(10):
                seq.append(float(cam._red_frame().mean()))
            lit = cam._grab(cfg.N_FRAMES, flush=False)
            elapsed = time.monotonic() - t0
        finally:
            cam.leds.off()
        lm, l99, lmax = stats(lit)
        final = seq[-1] - dm
        print(f"        frame means after LED on: {[round(v, 1) for v in seq]}  ({elapsed:.1f} s)")
        if final <= max(5.0, 0.02 * cam.full_scale):
            report("FAIL", "LEDs make no visible difference",
                   "check LED wiring/5 V rail/GND bond (run system_test.py), LED aim, ROI on the strip")
        else:
            first_ok = next((i for i, v in enumerate(seq) if v - dm >= 0.97 * final), len(seq))
            need = first_ok + 1
            ok = need <= cfg.FLUSH_FRAMES
            report("PASS" if ok else "WARN", "LED / frame timing",
                   f"first fully-lit frame = #{first_ok}; FLUSH_FRAMES={cfg.FLUSH_FRAMES}"
                   + ("" if ok else f"  -> set FLUSH_FRAMES = {need + 1} in hardware_config.py"))

        # 7. exposure level
        lit_minus_dark = lit - dark
        y0, y1, x0, x1 = analysis.roi_bounds(lit.shape, cfg.ROI)
        roi = lit_minus_dark[y0:y1, x0:x1]
        paper = float(np.percentile(roi, 80))
        sat = float(lit[y0:y1, x0:x1].max()) >= cfg.SATURATION_FRACTION * cam.full_scale
        pct = 100 * paper / cam.full_scale
        if sat:
            report("WARN", "exposure: TOO BRIGHT (saturated pixels in ROI)",
                   f"paper ~{pct:.0f}% of full scale -> lower CAM_EXPOSURE_US (now {cfg.CAM_EXPOSURE_US})")
        elif pct < 25:
            new = int(cfg.CAM_EXPOSURE_US * 55 / max(pct, 1))
            report("WARN", "exposure: low", f"paper ~{pct:.0f}% of full scale -> try CAM_EXPOSURE_US = {new}")
        elif pct > 85:
            report("WARN", "exposure: high", f"paper ~{pct:.0f}% -> lower CAM_EXPOSURE_US a little")
        else:
            report("PASS", "exposure", f"paper ~{pct:.0f}% of full scale (target 40-80%)")

        # 8. repeatability: two quick measurements of the same strip
        a1 = analysis.analyze(*cam.measure(), cfg, cam.full_scale)
        a2 = analysis.analyze(*cam.measure(), cfg, cam.full_scale)
        if a1["status"] == "OK" and a2["status"] == "OK":
            diff = abs(a1["absorbance"] - a2["absorbance"])
            report("PASS" if diff < 0.01 else "WARN", "repeat measurement",
                   f"A1={a1['absorbance']:.4f} A2={a2['absorbance']:.4f} diff={diff:.4f}"
                   + ("" if diff < 0.01 else "  -> check for light leaks / loose strip / LED flicker"))
        else:
            report("WARN", "repeat measurement skipped", f"status {a1['status']}, {a2['status']}")

        # 9. save pictures
        folder = os.path.join(storage.data_dir(cfg), "photos")
        stamp = storage.file_stamp()
        colour = os.path.join(folder, f"camtest_colour_{stamp}.jpg")
        cam.leds.on()
        try:
            cam._grab(1, save_path=colour)
        finally:
            cam.leds.off()
        dbg = os.path.join(folder, f"camtest_roi_{stamp}.png")
        storage.save_debug_image(cfg, lit_minus_dark, a2, dbg)
        report("PASS", "saved pictures", f"{colour}\n        {dbg}  (yellow = ROI, cyan = line found)")
    finally:
        cam.close()
        excite.off()

    fails = sum(1 for s, _ in RESULTS if s == "FAIL")
    warns = sum(1 for s, _ in RESULTS if s == "WARN")
    print(f"\n=== done: {fails} FAIL, {warns} WARN ===")
    print("Excitation LEDs are OFF.")


if __name__ == "__main__":
    main()
