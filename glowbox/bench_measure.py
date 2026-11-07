#!/usr/bin/env python3
"""
GlowBox - bench_measure.py
Keyboard-driven measurements over SSH, for setting up the box and for test series
(e.g. marker dilutions). Results go to glowbox_data/bench.csv.

At the prompt type:
  a label (e.g. "blue_1/4")  -> measure the strip in the box and log it with that label
  roi                        -> measure and save a picture: yellow = measuring box, cyan = line,
                                magenta = strip, red = other bright spots (LED glare)
  q                          -> quit
"""
from gpiozero import DigitalOutputDevice

import hardware_config as cfg
import analysis
import storage
from camera_reader import CameraReader


def main():
    excite = DigitalOutputDevice(cfg.GPIO_EXCITE, active_high=True, initial_value=False)
    cam = CameraReader(cfg, excite)
    calibration = storage.load_calibration(cfg)
    print(f"Raw full scale = {cam.full_scale}, Bayer = {cam.bayer}")
    print("Calibration:", calibration if calibration else "none yet")
    try:
        while True:
            label = input("\nlabel / roi / q > ").strip()
            if label.lower() in ("q", "quit", "exit"):
                break
            debug = label.lower() == "roi"
            photo = storage.photo_path(cfg, "bench")
            sample, dark = cam.measure(save_path=photo)
            r = analysis.analyze(sample, dark, cfg, cam.full_scale)

            print(f"status={r['status']}")
            if r["paper_level"] is not None:
                pct = 100 * r["paper_level"] / cam.full_scale
                print(f"paper level = {r['paper_level']:.1f} ({pct:.0f}% of full scale; aim for 40-80%)")
            if r["status"] == "OK":
                v = analysis.verdict(r["absorbance"], calibration)
                print(f"absorbance = {r['absorbance']:.4f}   verdict = {v}")
                print(f"line level = {r['line_level']:.1f}   line position in ROI = {r['line_pos']:.2f}"
                      f"   line runs {'left-right' if r['orientation'] == 'horizontal' else 'up-down'}")
            elif r["status"] == "TOO_BRIGHT":
                print("-> lower CAM_EXPOSURE_US (or CAM_GAIN) in hardware_config.py")
            elif r["status"] == "TOO_DARK":
                print("-> raise CAM_EXPOSURE_US in hardware_config.py, check LEDs and ROI")
            elif r["status"] == "NO_STRIP":
                print("-> no strip found: check the strip is in view and lit (aim the LEDs), "
                      "or raise CAM_EXPOSURE_US")

            if debug:
                path = storage.photo_path(cfg, "roi_debug") or "roi_debug.png"
                path = path.replace(".jpg", ".png")
                storage.save_debug_image(cfg, sample - dark, r, path)
                print(f"saved ROI picture: {path}")
            else:
                storage.append_csv(cfg, cfg.BENCH_CSV, {
                    "time": storage.timestamp(),
                    "label": label,
                    "status": r["status"],
                    "absorbance": storage.fmt(r["absorbance"]),
                    "line_level": storage.fmt(r["line_level"], 1),
                    "paper_level": storage.fmt(r["paper_level"], 1),
                    "line_pos": storage.fmt(r["line_pos"], 3),
                    "photo": photo or "",
                })
    except KeyboardInterrupt:
        pass
    finally:
        cam.close()
        excite.off()


if __name__ == "__main__":
    main()
