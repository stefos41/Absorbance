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
# Start LOW and raise only if readings say "TOO DARK". A white strip under red LEDs is bright.
CAM_EXPOSURE_US = 20_000  # 20 ms
CAM_GAIN = 1.0
CAM_LENS_POSITION = 6.5   # dioptres; 6.5 ~= 15 cm. Tune with bench_measure.py if blurry.
CAM_RAW_SIZE = (2304, 1296)   # binned sensor mode: fast, low noise
FLUSH_FRAMES = 4          # frames thrown away after every LED on/off change
N_FRAMES = 3              # frames averaged per measurement
N_DARK_FRAMES = 3         # frames averaged for the DARK (LEDs off) image

# ---------------- Strip / line geometry ----------------
# Region of interest (ROI) as fractions of the image: (top, bottom, left, right).
# It should cover the strip's reading window ONLY (no box walls, no holder edges).
# Use:  python3 bench_measure.py   then type  roi   to save a picture with this box drawn.
ROI = (0.15, 0.85, 0.40, 0.60)

# "horizontal" = the coloured line runs left-right across the image
#               (strip lies with its long side going up-down in the picture).
# "vertical"   = the line runs up-down in the image.
LINE_ORIENTATION = "horizontal"

# Sizes below are in red-channel pixels (about 0.17 mm each at 15 cm).
LINE_HALF_WIDTH_PX = 2    # half-width of the measured line band. Keep the band (2*this+1) NARROWER than the real line
BG_GAP_PX = 6             # gap between line band and background bands (skips blurry edges)
BG_WIDTH_PX = 15          # width of the clean-paper background band on EACH side
SMOOTH_PX = 3             # moving-average smoothing of the brightness profile

# ---------------- Image quality checks ----------------
MIN_PAPER_LEVEL = 30      # paper brightness (above dark) below this -> "TOO DARK"
SATURATION_FRACTION = 0.92  # any ROI pixel above this fraction of full scale -> "TOO BRIGHT"

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
