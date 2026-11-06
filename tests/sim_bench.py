import os
HERE = os.path.dirname(os.path.abspath(__file__))
import sys, time, builtins
sys.path.insert(0, os.path.join(HERE, "fakes")); sys.path.insert(0, os.path.join(HERE, "..", "glowbox"))
time.sleep = lambda s: None
import gpiozero, picamera2, hardware_config as cfg
import tempfile; cfg.DATA_DIR = tempfile.mkdtemp(prefix="gb_")
import bench_measure
_orig = gpiozero.DigitalOutputDevice.__init__
def init(self, *a, **k):
    _orig(self, *a, **k)
    if self.pin == 17: picamera2.STATE["led"] = lambda: self.value == 1
gpiozero.DigitalOutputDevice.__init__ = init
inputs = iter(["blue_full", "roi", "q"]); builtins.input = lambda p="": next(inputs)
bench_measure.main()
