# Absorbance — GlowBox test-strip reader

A low-cost Raspberry Pi device that reads coloured test-strip lines under 650 nm red light, measures how much light the line absorbs, and shows the **absorbance** and a **POS/NEG** verdict on a 16×2 LCD. It replaces "is that a faint line or not?" by eye with an objective, logged number.

**Status (November 2026):** working prototype, tested on real hardware with marker-line strips. Starts automatically at power-on; runs with just the button and LCD.

## How it works

1. Red 650 nm LEDs light the strip from the side inside a dark enclosure; the camera looks straight down.
2. The code finds the strip in the photo (any position or direction), then the darkest line across it.
3. **Absorbance = −log10(line brightness ÷ paper brightness)**, both measured above an LEDs-off dark frame. Blue, purple and black lines absorb red light, so more dye gives a higher number.
4. **POS** if the absorbance is above a threshold set by calibration with blank strips (blank mean + 3 × standard deviation).

## Results (prototype, 2026-11-06)

| Measurement | Value |
|---|---|
| Blank strips (n = 10), mean absorbance | 0.0076 |
| Blank strips, standard deviation | 0.0013 |
| POS/NEG threshold (detection limit) | **0.0126**: a line absorbing ~3% of the red light |
| Repeatability, same strip not moved | ±0.0004 |
| Repeatability, strip re-inserted in holder | ±0.007 on a 0.72 line (~1%) |

| Test strip | Absorbance | LCD result |
|---|---|---|
| Blank paper | 0.006 | NEG ✓ |
| Dark blue/black marker line | 0.693 | POS ✓ |
| Faint marker line | 0.232 | POS ✓ |
| Red marker line | 0.110 | POS: red ink absorbs some 650 nm light, ~6× weaker than blue/black |

Raw data: [`results/`](results/).

## Using the device

| Button | Action |
|---|---|
| Short press | Read the strip. The result (e.g. `A=0.693 POS`, threshold, reading #) stays on the LCD until the next press |
| Hold 3 s | Calibrate: insert and press for 10 blank strips |
| Hold 10 s | Safe shutdown. Wait ~20 s, then unplug. Plug back in to start again |

Readings, calibration and a photo of every reading are saved in `glowbox/glowbox_data/` on the Pi.

## Repository

* `glowbox/`: code that runs on the Pi. Setup and usage: [glowbox/README.md](glowbox/README.md)
* `docs/HARDWARE.md`: parts, pin map, wiring, safety checklist
* `deploy/glowbox.service`: auto-start at boot
* `results/`: prototype data and tuned settings
* `tests/`: hardware-free simulations with fake GPIO and camera. Run `bash tests/run_all.sh` (needs `numpy` and `pillow`)

## Quick start on the Pi

```bash
git clone https://github.com/stefos41/Absorbance.git
cd Absorbance/glowbox
sudo apt install -y python3-picamera2 python3-gpiozero python3-lgpio python3-numpy python3-pil
python3 system_test.py          # wiring
python3 camera_test.py --apply  # camera + save a good exposure for this setup
python3 camera_test.py          # confirm
python3 bench_measure.py        # check strip finding ("roi") and repeatability
python3 glowbox.py              # the device (hold 3 s to calibrate)
```

Per-setup tuning (exposure, gain) is saved in `glowbox/local_settings.py` on the Pi, which git ignores. The prototype's values are kept in [`results/`](results/) for reference.

## Limitations and next steps

* A measurement tool for research and education, **not a diagnostic device**.
* Reports the darkest single line. Real commercial strips have a test **and** a control line, so they need a test/control mode (planned).
* Red light reads blue, purple and black lines. Red/pink (gold-nanoparticle) lines need added green ~525 nm LEDs (planned).
* The line search skips the first 20% of the strip at the holder end (`LINE_SEARCH`), so draw lines away from that end.
* Even LED lighting improves sensitivity; diffusing or adding LEDs helps.
