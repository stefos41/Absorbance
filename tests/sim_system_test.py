import os
HERE = os.path.dirname(os.path.abspath(__file__))
import sys, time
sys.path.insert(0, os.path.join(HERE, "fakes")); sys.path.insert(0, os.path.join(HERE, "..", "glowbox"))
time.sleep = lambda s: None
import gpiozero; gpiozero.PRESSES.append("short")
import system_test; system_test.main()
