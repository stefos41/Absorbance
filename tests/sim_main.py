import os
HERE = os.path.dirname(os.path.abspath(__file__))
import sys, time
sys.path.insert(0, os.path.join(HERE, "fakes")); sys.path.insert(0, os.path.join(HERE, "..", "glowbox"))
time.sleep = lambda s: None
_t=[0.0]
def mono(): _t[0]+=0.01; return _t[0]
time.monotonic = mono
import gpiozero, picamera2
import hardware_config as cfg
import tempfile; cfg.DATA_DIR = tempfile.mkdtemp(prefix="gb_")
import glowbox
orig = glowbox.Hardware.__init__
def init(self):
    orig(self)
    picamera2.STATE["led"] = lambda: self.excite.value == 1
    self.lcd.show = lambda a="", b="": print(f"   LCD |{a[:16]:<16}|{b[:16]:<16}|")
glowbox.Hardware.__init__ = init
gpiozero.PRESSES.extend(["short", "long"] + ["short"]*10 + ["short"])
glowbox.main()
print("final excite state:", [e for e in gpiozero.LOG if e[1]==17][-1])
