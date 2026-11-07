#!/usr/bin/env python3
"""
GlowBox - camera_test.py
Step-by-step camera check. Prints PASS / WARN / FAIL for each step and saves test pictures.

Run with a strip (or white paper) in the holder and the box closed:
    python3 camera_test.py            # tests the mode set in hardware_config.CAM_MODE
    python3 camera_test.py rgb        # force the fallback (processed colour) mode
    python3 camera_test.py raw        # force raw mode
    python3 camera_test.py --apply    # also SAVE the suggested exposure/gain (local_settings.py)

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


def apply_settings(updates):
    """Merge updates into glowbox/local_settings.py (not tracked by git)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_settings.py")
    current = {}
    if os.path.exists(path):
        exec(open(path).read(), {}, current)
    current.update(updates)
    with open(path, "w") as f:
        f.write("# Written by camera_test.py --apply on " + storage.timestamp() + "\n")
        f.write("# Overrides hardware_config.py on this Pi only. Delete this file to undo.\n")
        for k, v in current.items():
            f.write(f"{k} = {v!r}\n")
    return path


def stats(img):
    return float(img.mean()), float(np.percentile(img, 99)), float(img.max())


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    modes = [a for a in args if a in ("raw", "rgb", "auto")]
    mode = modes[0] if modes else None
    suggestion = None
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

        # 6. LEDs on: keep every frame right after switching on (no flushing) to check timing
        cam.picam2.capture_request().release()
        frames = []
        try:
            cam.leds.on()
            t0 = time.monotonic()
            for _ in range(10):
                frames.append(cam._red_frame())
            lit = cam._grab(cfg.N_FRAMES, flush=False)
            elapsed = time.monotonic() - t0
        finally:
            cam.leds.off()
        lit_minus_dark = lit - dark

        # 7. find the strip
        roi_px, orientation, strip = analysis.resolve_roi(lit, dark, cfg)
        if roi_px is None:
            report("FAIL", "no strip found in the picture",
                   "is the strip under the camera and lit? aim the LEDs at it; "
                   "if the picture is very dark, raise CAM_EXPOSURE_US")
            region = (0, lit.shape[0], 0, lit.shape[1])
        else:
            region = strip["strip_px"] if strip else roi_px
            if strip:
                sy0, sy1, sx0, sx1 = strip["strip_px"]
                h, w = lit.shape
                report("PASS", "strip found",
                       f"strip at x {100*sx0/w:.0f}-{100*sx1/w:.0f}%, y {100*sy0/h:.0f}-{100*sy1/h:.0f}% of the image; "
                       f"line runs {'left-right' if orientation == 'horizontal' else 'up-down'}")
                bright = [o for o in strip["others"] if o[4] > 0.5 * cam.full_scale]
                if bright:
                    report("WARN", f"{len(bright)} bright spot(s) outside the strip",
                           "probably an LED (or its reflection) visible to the camera -> angle it away "
                           "or shield it with black card (red boxes in the camtest_roi picture)")
                else:
                    report("PASS", "no LED glare visible")

        # 8. LED timing, measured on the strip only
        ry0, ry1, rx0, rx1 = region
        seq = [float(fr[ry0:ry1, rx0:rx1].mean()) for fr in frames]
        base = float(dark[ry0:ry1, rx0:rx1].mean())
        final = seq[-1] - base
        print(f"        strip brightness after LED on: {[round(v, 1) for v in seq]}  ({elapsed:.1f} s)")
        if final <= max(5.0, 0.02 * cam.full_scale):
            report("FAIL", "LEDs make almost no difference on the strip",
                   "aim the LEDs at the strip (live preview: pinctrl set 17 op dh; rpicam-hello -t 0), "
                   "move them closer, add LEDs, or raise CAM_EXPOSURE_US / CAM_GAIN")
        else:
            first_ok = next((i for i, v in enumerate(seq) if v - base >= 0.97 * final), len(seq))
            need = first_ok + 1
            ok = need <= cfg.FLUSH_FRAMES
            report("PASS" if ok else "WARN", "LED / frame timing",
                   f"first fully-lit frame = #{first_ok}; FLUSH_FRAMES={cfg.FLUSH_FRAMES}"
                   + ("" if ok else f"  -> set FLUSH_FRAMES = {need + 1} in hardware_config.py"))

        # 9. exposure level on the measuring box
        if roi_px is not None:
            y0, y1, x0, x1 = roi_px
            paper = float(np.percentile(lit_minus_dark[y0:y1, x0:x1], 80))
            sat = float(lit[y0:y1, x0:x1].max()) >= cfg.SATURATION_FRACTION * cam.full_scale
            pct = 100 * paper / cam.full_scale
            exp, gain = cfg.CAM_EXPOSURE_US, cfg.CAM_GAIN
            sat_level = cfg.SATURATION_FRACTION * cam.full_scale
            sat_pct = 100 * float(np.mean(lit[y0:y1, x0:x1] >= sat_level))
            if sat:
                # paper level (80th percentile) is still measurable: aim it at ~40%,
                # which keeps hotspots up to ~2x brighter than the paper below the maximum
                scale = min(40 / max(pct, 1.0), 0.8)
                new_exp = max(int(exp * scale), 1000)
                suggestion = {"CAM_EXPOSURE_US": new_exp, "CAM_GAIN": gain}
                report("WARN", "exposure: TOO BRIGHT (saturated pixels on the strip)",
                       f"paper ~{pct:.0f}% of full scale, {sat_pct:.2f}% of strip pixels maxed out "
                       f"-> try CAM_EXPOSURE_US = {new_exp}"
                       + ("  (bright hotspots: more even LED light would help)" if sat_pct < 5 and pct < 60 else ""))
            elif pct < 30 or pct > 85:
                factor = 50 / max(pct, 0.5)
                new_exp, new_gain = exp * factor, gain
                while new_exp > 300_000 and new_gain < 8:
                    new_exp, new_gain = new_exp / 2, new_gain * 2
                new_exp = int(new_exp)
                suggestion = {"CAM_EXPOSURE_US": new_exp, "CAM_GAIN": float(new_gain)}
                tip = f"-> try CAM_EXPOSURE_US = {new_exp}" + (
                    f" and CAM_GAIN = {new_gain:.1f}" if new_gain != gain else "")
                if new_exp > 1_000_000:
                    tip += "  (that is very long: better to aim the LEDs at the strip and add more LEDs)"
                report("WARN", f"exposure: {'low' if pct < 30 else 'high'}",
                       f"paper ~{pct:.0f}% of full scale (target 40-80%) {tip}")
            else:
                report("PASS", "exposure", f"paper ~{pct:.0f}% of full scale (target 40-80%)")

        # 10. repeatability: two quick measurements of the same strip
        a1 = analysis.analyze(*cam.measure(), cfg, cam.full_scale)
        a2 = analysis.analyze(*cam.measure(), cfg, cam.full_scale)
        if a1["status"] == "OK" and a2["status"] == "OK":
            diff = abs(a1["absorbance"] - a2["absorbance"])
            report("PASS" if diff < 0.01 else "WARN", "repeat measurement",
                   f"A1={a1['absorbance']:.4f} A2={a2['absorbance']:.4f} diff={diff:.4f}"
                   + ("" if diff < 0.01 else "  -> check for light leaks / loose strip / LED flicker"))
        else:
            report("WARN", "repeat measurement skipped", f"status {a1['status']}, {a2['status']}")

        # 11. save pictures
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
        report("PASS", "saved pictures", f"{colour}\n        {dbg}\n        (yellow = measuring box, cyan = line, magenta = strip, red = bright spots)")
    finally:
        cam.close()
        excite.off()

    if suggestion:
        if apply:
            path = apply_settings(suggestion)
            print(f"\n>>> Saved {suggestion} to {path}")
            print(">>> Run  python3 camera_test.py  again to check it.")
        else:
            print("\n>>> To save the suggested settings automatically, run:  python3 camera_test.py --apply")

    fails = sum(1 for s, _ in RESULTS if s == "FAIL")
    warns = sum(1 for s, _ in RESULTS if s == "WARN")
    print(f"\n=== done: {fails} FAIL, {warns} WARN ===")
    print("Excitation LEDs are OFF.")


if __name__ == "__main__":
    main()
