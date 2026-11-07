"""
GlowBox - hardware_config.py
All pin numbers and tunable settings live here. Change values here, not in the other files.
Pin numbers are BCM (GPIO) numbers, not physical header pin numbers.
"""

# ---------------- GPIO pins (BCM numbering) ----------------
GPIO_EXCITE = 17          # MOSFET gate (via 330 ohm) -> red LED bank. HIGH = LEDs ON
GPIO_BUTTON = 27          # Button to GND, internal pull-up. LOW = pressed
GPIO_GREEN = 22           # Green status LED ("ready")
GPIO_RED = 23             # Red status LED ("captured" / error)

LCD_RS = 5
LCD_E = 6
LCD_DATA = [12, 13, 19, 26]   # D4, D5, D6, D7  (LCD R/W pin MUST be wired to GND)

# ---------------- Button behaviour ----------------
DEBOUNCE_S = 0.05         # ignore contact bounce shorter than this
HOLD_FOR_CAL_S = 3.0      # hold the button this long to enter calibration mode
RESULT_SHOW_S = 1.5       # how long the red LED flashes after a reading

# ---------------- LED safety ----------------
LED_SETTLE_S = 0.10       # wait after switching LEDs on before capturing
LED_MAX_ON_S = 10.0       # watchdog: LEDs are forced off after this many seconds

# ---------------- Camera ----------------
# "auto" = use raw sensor data if it works, otherwise fall back to the normal colour image.
# "raw"  = raw only (most accurate).  "rgb" = normal colour image only (most robust).
CAM_MODE = "auto"
# camera_test.py tells you if these need changing (and suggests values).
CAM_EXPOSURE_US = 150_000  # 150 ms: 250 ms saturated hotspots (paper ~50%), so ~0.6x
CAM_GAIN = 8.0
CAM_LENS_POSITION = 6.5   # dioptres; 6.5 ~= 15 cm. Tune with bench_measure.py if blurry.
CAM_RAW_SIZE = (2304, 1296)   # binned sensor mode: fast, low noise
FLUSH_FRAMES = 4          # frames thrown away after every LED on/off change
N_FRAMES = 3              # frames averaged per measurement
N_DARK_FRAMES = 3         # frames averaged for the DARK (LEDs off) image

# ---------------- Strip / line geometry ----------------
# Where to measure.
#   ROI = "auto"  -> the code finds the strip (the largest bright area) in every photo.
#   ROI = (top, bottom, left, right) as fractions of the image -> fixed box instead.
# Use camera_test.py or "roi" in bench_measure.py to see the box it uses (yellow).
ROI = "auto"

# Which way the coloured LINE runs in the camera image.
#   "auto"       -> decided from the strip's shape: a strip lying left-right has
#                   lines running up-down, and vice versa (true for test strips).
#   "horizontal" -> line runs left-right.   "vertical" -> line runs up-down.
LINE_ORIENTATION = "auto"

# Auto-ROI tuning (rarely needs changing)
AUTO_MIN_AREA_FRAC = 0.01     # strip must cover at least 1% of the image
AUTO_MIN_CONTRAST = 8         # strip must be at least this much brighter than the background (raw units)
AUTO_JOIN_FRAC = 0.30         # parts of the strip down to 30% of its brightness still count (uneven light)
AUTO_MARGIN_ACROSS = 0.20     # trim 20% off each long edge of the strip (blurry edges)
AUTO_MARGIN_ALONG = 0.04      # trim 4% off each short end (keep lines near the ends)

# Sizes below are in red-channel pixels (about 0.17 mm each at 15 cm).
LINE_HALF_WIDTH_PX = 2    # half-width of the measured line band. Keep the band (2*this+1) NARROWER than the real line
BG_GAP_PX = 6             # gap between line band and background bands (skips blurry edges)
BG_WIDTH_PX = 15          # width of the clean-paper background band on EACH side
SMOOTH_PX = 3             # moving-average smoothing of the brightness profile

# Where along the strip to look for the line, as fractions of the measuring box:
# 0.0 = top end (lines running left-right) or left end (lines running up-down).
# (0.20, 1.0) skips the first 20% at the holder end, where the L-holder's edge and
# shadow look like a line. Draw marker lines away from that end.
LINE_SEARCH = (0.20, 1.0)
# Reject "lines" whose paper above and below differs by more than this fraction
# (edges and shadows have paper on one side only). 1.0 = check off.
BG_MAX_MISMATCH = 0.30

# ---------------- Image quality checks ----------------
MIN_PAPER_LEVEL = 30      # paper brightness (above dark) below this -> "TOO DARK"
SATURATION_FRACTION = 0.92  # a pixel above this fraction of full scale counts as maxed out
SAT_MAX_FRACTION = 0.02     # "TOO BRIGHT" only if >2% of the measured area is maxed out;
                            # fewer maxed-out pixels (glints) are simply left out

# ---------------- Calibration / decision ----------------
CAL_N_BLANKS = 10         # blank (no line) strips measured during calibration
CAL_K_SIGMA = 3.0         # threshold = blank mean + K * blank standard deviation
CAL_MIN_DELTA = 0.005     # threshold is at least blank mean + this (avoids zero-width thresholds)

# ---------------- Files ----------------
DATA_DIR = "glowbox_data"             # created next to the scripts
CAL_FILE = "calibration.json"
READINGS_CSV = "readings.csv"
BENCH_CSV = "bench.csv"
SAVE_PHOTOS = True

# ---------------- Per-setup overrides ----------------
# camera_test.py --apply writes tuned values (e.g. exposure) to local_settings.py next to
# this file. That file is NOT in git, so tuning on the Pi never conflicts with git pull.
# Delete local_settings.py to go back to the values above.
try:
    from local_settings import *  # noqa: F401,F403
except ImportError:
    pass
