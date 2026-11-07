import os
HERE = os.path.dirname(os.path.abspath(__file__))
import sys, time, tempfile, subprocess
sys.path.insert(0, os.path.join(HERE, "fakes")); sys.path.insert(0, os.path.join(HERE, "..", "glowbox"))
time.sleep = lambda s: None
_t = [0.0]
def mono(): _t[0] += 0.01; return _t[0]
time.monotonic = mono
import gpiozero, picamera2, hardware_config as cfg
cfg.DATA_DIR = tempfile.mkdtemp(prefix="gb_")
import glowbox
LCD = []
orig = glowbox.Hardware.__init__
def init(self):
    orig(self)
    picamera2.STATE["led"] = lambda: self.excite.value == 1
    self.lcd.show = lambda a="", b="": (LCD.append((a, b)), print(f"   LCD |{a[:16]:<16}|{b[:16]:<16}|"))
    self.lcd.close = lambda: LCD.append(("<closed>", ""))
glowbox.Hardware.__init__ = init
calls = []
fail = "fail" in sys.argv
glowbox.subprocess.call = lambda cmd: (calls.append(cmd), 1 if fail else 0)[1]
gpiozero.PRESSES.extend(["short", "shutdown"] + (["short", "short"] if fail else []))
glowbox.main()
print("shutdown command:", calls)
ok = calls == [["sudo", "-n", "shutdown", "-h", "now"]]
if fail:
    ok = ok and ("SHUTDOWN FAILED", "see terminal") in LCD and LCD[-1] == ("<closed>", "")
else:
    ok = ok and LCD[-1] == ("Shutting down", "unplug in 20 s")
ex = [e for e in gpiozero.LOG if e[1] == 17][-1]
print("excite LEDs:", ex[0]); ok = ok and ex[0] == "off"
print("SHUTDOWN SIM:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
