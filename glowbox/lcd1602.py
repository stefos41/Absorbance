"""
GlowBox - lcd1602.py
Minimal HD44780 (1602A) driver, 4-bit mode, write-only, using gpiozero.
Wiring: RS, E, D4-D7 to GPIO; R/W (LCD pin 5) MUST go to GND.
"""
import time
from gpiozero import DigitalOutputDevice


class LCD1602:
    COLS = 16
    ROW_ADDR = (0x00, 0x40)

    def __init__(self, rs, e, data_pins):
        if len(data_pins) != 4:
            raise ValueError("data_pins must be [D4, D5, D6, D7]")
        self.rs = DigitalOutputDevice(rs, initial_value=False)
        self.e = DigitalOutputDevice(e, initial_value=False)
        self.d = [DigitalOutputDevice(p, initial_value=False) for p in data_pins]
        self._init_display()

    # ---- low level ----
    def _pulse(self):
        self.e.on()
        time.sleep(0.000002)
        self.e.off()
        time.sleep(0.00005)   # most commands need ~37 us

    def _write4(self, nibble):
        for i, pin in enumerate(self.d):
            pin.value = (nibble >> i) & 1
        self._pulse()

    def _send(self, byte, is_data):
        self.rs.value = 1 if is_data else 0
        self._write4(byte >> 4)
        self._write4(byte & 0x0F)

    def command(self, byte):
        self._send(byte, False)
        if byte in (0x01, 0x02):      # clear / home are slow
            time.sleep(0.002)

    def _init_display(self):
        time.sleep(0.05)
        self.rs.off()
        for delay in (0.005, 0.005, 0.001):   # reset sequence from the datasheet
            self._write4(0x03)
            time.sleep(delay)
        self._write4(0x02)            # switch to 4-bit mode
        time.sleep(0.001)
        self.command(0x28)            # 4-bit, 2 lines, 5x8 font
        self.command(0x0C)            # display on, cursor off, blink off
        self.command(0x06)            # cursor moves right, no shift
        self.clear()

    # ---- user functions ----
    def clear(self):
        self.command(0x01)

    def write_line(self, row, text):
        """Write text to row 0 or 1, padded/truncated to 16 characters."""
        text = str(text)[: self.COLS].ljust(self.COLS)
        self.command(0x80 | self.ROW_ADDR[row])
        for ch in text:
            code = ord(ch)
            self._send(code if 32 <= code < 127 else ord("?"), True)

    def show(self, line1="", line2=""):
        self.write_line(0, line1)
        self.write_line(1, line2)

    def close(self):
        for dev in [self.rs, self.e] + self.d:
            dev.close()
