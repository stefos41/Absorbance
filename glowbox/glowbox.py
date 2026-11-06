#!/usr/bin/env python3
"""
GlowBox - glowbox.py  (main program)

Short press  : read one strip -> LCD shows absorbance and POS/NEG
Hold 3 s     : calibration mode -> measure blank strips to set the POS/NEG threshold

Run:  python3 glowbox.py      (Ctrl+C to quit)
"""
import signal
import sys
import time

from gpiozero import Button, DigitalOutputDevice, LED

import hardware_config as cfg
import analysis
import storage
from lcd1602 import LCD1602


class Hardware:
    def __init__(self):
        # EXCITE starts OFF; the 10k gate pull-down also holds it off during boot
        self.excite = DigitalOutputDevice(cfg.GPIO_EXCITE, active_high=True, initial_value=False)
        self.green = LED(cfg.GPIO_GREEN)
        self.red = LED(cfg.GPIO_RED)
        self.button = Button(cfg.GPIO_BUTTON, pull_up=True, bounce_time=cfg.DEBOUNCE_S)
        self.lcd = LCD1602(cfg.LCD_RS, cfg.LCD_E, cfg.LCD_DATA)

    def wait_press(self, lcd_hint=None):
        """Wait for a press. Returns 'short' or 'long' (held >= HOLD_FOR_CAL_S)."""
        self.button.wait_for_press()
        t0 = time.monotonic()
        announced = False
        while self.button.is_pressed:
            if not announced and time.monotonic() - t0 >= cfg.HOLD_FOR_CAL_S:
                announced = True
                if lcd_hint:
                    self.lcd.show(*lcd_hint)
            time.sleep(0.01)
        time.sleep(cfg.DEBOUNCE_S)
        return "long" if announced else "short"

    def safe_off(self):
        self.excite.off()
        self.green.off()

    def close(self):
        self.excite.off()
        self.green.off()
        self.red.off()
        try:
            self.lcd.clear()
            self.lcd.close()
        except Exception:
            pass


def short_status(status):
    return {"TOO_DARK": "TOO DARK", "TOO_BRIGHT": "TOO BRIGHT"}.get(status, status)


def do_reading(hw, cam, calibration, count):
    hw.lcd.show("Reading...", "")
    path = storage.photo_path(cfg, f"read{count:04d}")
    sample, dark = cam.measure(save_path=path)
    result = analysis.analyze(sample, dark, cfg, cam.full_scale)
    v = analysis.verdict(result["absorbance"], calibration)

    storage.append_csv(cfg, cfg.READINGS_CSV, {
        "time": storage.timestamp(),
        "reading": count,
        "status": result["status"],
        "absorbance": storage.fmt(result["absorbance"]),
        "verdict": v,
        "threshold": storage.fmt(calibration["threshold"]) if calibration else "",
        "line_level": storage.fmt(result["line_level"], 1),
        "paper_level": storage.fmt(result["paper_level"], 1),
        "line_pos": storage.fmt(result["line_pos"], 3),
        "photo": path or "",
    })

    if result["status"] != "OK":
        hw.lcd.show(short_status(result["status"]), "check exposure")
        print(f"[{count}] {result['status']} paper_level={result['paper_level']}")
    else:
        a = result["absorbance"]
        hw.lcd.show(f"A={a:.3f} {v}",
                    f"thr={calibration['threshold']:.3f}" if calibration else "NO CAL:hold 3s")
        print(f"[{count}] A={a:.4f} {v}  line={result['line_level']:.1f} "
              f"paper={result['paper_level']:.1f} pos={result['line_pos']:.2f}")

    hw.red.on()
    time.sleep(cfg.RESULT_SHOW_S)
    hw.red.off()


def do_calibration(hw, cam):
    """Measure CAL_N_BLANKS blank strips. Hold the button to finish early (min 3)."""
    values = []
    hint = ("Release to", "finish/cancel")
    while len(values) < cfg.CAL_N_BLANKS:
        hw.lcd.show(f"CAL blank {len(values) + 1}/{cfg.CAL_N_BLANKS}", "insert + press")
        hw.green.on()
        press = hw.wait_press(lcd_hint=hint)
        hw.green.off()
        if press == "long":
            break
        hw.lcd.show("Measuring blank", "")
        sample, dark = cam.measure()
        result = analysis.analyze(sample, dark, cfg, cam.full_scale)
        if result["status"] != "OK":
            hw.lcd.show(short_status(result["status"]), "not counted")
            time.sleep(2)
            continue
        values.append(result["absorbance"])
        print(f"  blank {len(values)}: A={result['absorbance']:.4f}")

    if len(values) < 3:
        hw.lcd.show("CAL cancelled", "need >= 3 blanks")
        time.sleep(2)
        return None

    cal = storage.save_calibration(cfg, analysis.compute_threshold(
        values, cfg.CAL_K_SIGMA, cfg.CAL_MIN_DELTA))
    print(f"Calibration saved: {cal}")
    hw.lcd.show("CAL saved", f"thr={cal['threshold']:.4f}")
    time.sleep(3)
    return cal


def main():
    # Turn SIGTERM (e.g. from systemd) into a normal exit so 'finally' runs
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    hw = Hardware()
    cam = None
    try:
        hw.lcd.show("GLOWBOX", "starting camera")
        try:
            from camera_reader import CameraReader
            cam = CameraReader(cfg, hw.excite)
        except Exception as e:
            hw.lcd.show("NO CAMERA", str(e)[:16])
            hw.red.on()
            print(f"Camera failed to start: {e!r}")
            print("Press the button (or Ctrl+C) to exit.")
            hw.wait_press()
            return

        calibration = storage.load_calibration(cfg)
        count = 0
        while True:
            hw.green.on()
            hw.lcd.show("GLOWBOX READY", "press=read" if calibration else "hold 3s = CAL")
            press = hw.wait_press(lcd_hint=("Release for", "CALIBRATION"))
            hw.green.off()
            try:
                if press == "long":
                    new_cal = do_calibration(hw, cam)
                    if new_cal:
                        calibration = new_cal
                else:
                    count += 1
                    do_reading(hw, cam, calibration, count)
            except Exception as e:
                hw.safe_off()                    # LEDs off immediately on any error
                hw.red.on()
                hw.lcd.show("ERROR", str(e)[:16])
                print(f"ERROR: {e!r}")
                hw.wait_press()
                hw.red.off()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if cam:
            cam.close()
        hw.close()


if __name__ == "__main__":
    main()
