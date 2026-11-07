import os
HERE = os.path.dirname(os.path.abspath(__file__))
import sys, time
sys.path.insert(0, os.path.join(HERE, "fakes")); sys.path.insert(0, os.path.join(HERE, "..", "glowbox"))
time.sleep = lambda s: None
import gpiozero, picamera2, hardware_config as cfg
import tempfile; cfg.DATA_DIR = tempfile.mkdtemp(prefix="gb_")
_orig = gpiozero.DigitalOutputDevice.__init__
def init(self, *a, **k):
    _orig(self, *a, **k)
    if self.pin == 17: picamera2.STATE["led"] = lambda: self.value == 1
gpiozero.DigitalOutputDevice.__init__ = init
if "broken" in sys.argv: picamera2.STATE["raw_broken"] = True
if "lag6" in sys.argv: picamera2.STATE["lag"] = 6
if "wide" in sys.argv: picamera2.STATE["layout"] = "strip_horizontal"
if "glare" in sys.argv: picamera2.STATE["glare"] = True
if "dim" in sys.argv: picamera2.STATE["paper"] = 12.0
sys.argv = ["camera_test.py"] + [a for a in sys.argv[1:] if a in ("rgb", "raw")]
import camera_test; camera_test.main()
