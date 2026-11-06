#!/usr/bin/env python3
"""
GlowBox - system_test.py
Checks the wiring one part at a time. Needs NO camera, so it also runs on the Pi 1 B+.

Before running: 5 V rail connected, Pi GND bonded to the GND rail, LCD R/W (pin 5) to GND.
"""
import time

from gpiozero import Button, DigitalOutputDevice, LED

import hardware_config as cfg


def step(msg):
    print(f"\n== {msg}")


def main():
    excite = DigitalOutputDevice(cfg.GPIO_EXCITE, active_high=True, initial_value=False)
    green, red = LED(cfg.GPIO_GREEN), LED(cfg.GPIO_RED)
    button = Button(cfg.GPIO_BUTTON, pull_up=True, bounce_time=cfg.DEBOUNCE_S)
    lcd = None
    try:
        step("GREEN status LED on for 2 s")
        green.on(); time.sleep(2); green.off()

        step("RED status LED on for 2 s")
        red.on(); time.sleep(2); red.off()

        step("Excitation LEDs (via MOSFET) on for 2 s")
        print("   If nothing lights: check 5 V rail, GND bond, MOSFET pin order (G-D-S), LED polarity.")
        excite.on(); time.sleep(2); excite.off()

        step("LCD test")
        try:
            from lcd1602 import LCD1602
            lcd = LCD1602(cfg.LCD_RS, cfg.LCD_E, cfg.LCD_DATA)
            lcd.show("GLOWBOX TEST", "0123456789ABCDEF")
            print("   LCD should show 'GLOWBOX TEST'. If blank or solid boxes: turn the contrast pot.")
        except Exception as e:
            print(f"   LCD failed: {e!r}")

        step("Button: press it within 15 s")
        if button.wait_for_press(timeout=15):
            print("   Button OK")
            if lcd:
                lcd.show("BUTTON OK", "")
            green.on(); time.sleep(1); green.off()
        else:
            print("   No press seen: check button legs straddle the trench, one side GPIO27, other GND.")

        print("\nSystem test finished.")
    finally:
        excite.off(); green.off(); red.off()
        if lcd:
            time.sleep(1)
            lcd.close()


if __name__ == "__main__":
    main()
