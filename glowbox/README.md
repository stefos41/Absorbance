# GlowBox: absorbance strip reader

The box lights a test strip with red LEDs, photographs it, and measures how much darker the coloured line is than the clean paper beside it:

    absorbance = -log10(line brightness / paper brightness)     (both measured above the LEDs-off "dark" level)

Higher absorbance means more dye on the line. A calibration with blank strips sets the POS/NEG threshold at blank mean + 3 × blank SD.

## Files

| File | What it does |
|---|---|
| `hardware_config.py` | **All settings**: pins, camera exposure, strip region (ROI), thresholds. Edit only this file. |
| `system_test.py` | Tests LEDs, MOSFET, LCD, button one at a time. No camera needed (runs on the Pi 1 too). |
| `camera_test.py` | Step-by-step camera check: detection, LED/frame timing, exposure, repeatability. Prints PASS/WARN/FAIL with the fix. |
| `bench_measure.py` | Keyboard tool over SSH: set up exposure/ROI, run marker or dilution series → `bench.csv`. |
| `glowbox.py` | The main program (button + LCD). |
| `analysis.py`, `camera_reader.py`, `lcd1602.py`, `storage.py` | Helpers used by the scripts above. |

Results are saved in `glowbox_data/`: `readings.csv`, `bench.csv`, `calibration.json` and `photos/`.

## 1. Install the operating system (Pi 4)

1. On your computer, install **Raspberry Pi Imager** from raspberrypi.com/software.
2. Device: **Raspberry Pi 4**. OS: **Raspberry Pi OS (64-bit)**, the recommended one at the top of the list.
   * Choose the normal version (with desktop) if you'll plug in a monitor. It's the easiest way to look at the saved photos.
   * Choose **Raspberry Pi OS Lite (64-bit)** if you'll only use it over SSH (no monitor).
3. In Imager's settings, set hostname `glowbox`, a username/password, your WiFi, and **enable SSH**. Write the SD card.
4. Boot the Pi with the camera ribbon already connected (power off when plugging the ribbon).

## 2. Install the Python packages

On the Pi (in a terminal or over `ssh youruser@glowbox.local`):

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-gpiozero python3-lgpio python3-numpy python3-pil
```

On the Lite OS, add `--no-install-recommends` after `install` to skip the desktop extras. On the desktop OS most of these are already installed.

Check the camera is detected:

```bash
rpicam-hello --list-cameras        # older OS versions: libcamera-hello --list-cameras
```

You should see `imx708_noir`.

## 3. Copy the code to the Pi

On the Pi:

```bash
git clone https://github.com/stefos41/Absorbance.git   # on the Pi
```

Then: `cd ~/Absorbance/glowbox`. Later updates: `git pull`.

## 4. Bring-up order

1. **Wiring test:** `python3 system_test.py`. Every part should respond. Turn the LCD contrast pot until text is crisp.
2. **Camera test:** put a strip or white paper in the holder, close the box, run `python3 camera_test.py`. Fix any WARN/FAIL using the hint it prints. If the camera won't start, try `python3 camera_test.py rgb`; if that works, set `CAM_MODE = "rgb"` in `hardware_config.py`.
3. **Exposure and strip finding:** put a strip with a marker line in the holder (either direction is fine), close the box, run `python3 bench_measure.py`, then:
   * Type `roi` and open the saved `glowbox_data/photos/roi_debug_*.png`. The code finds the strip by itself: **magenta** = the strip it found, **yellow** = the measuring box, **cyan** = the line it found, **orange** = where the line search starts/ends, **red** = other bright spots (usually an LED the camera can see; shield or re-aim it).
   * Check the printed **paper level**. Aim for 40–80% of full scale. If `camera_test.py` says TOO BRIGHT or low, run `python3 camera_test.py --apply`: it saves the suggested exposure/gain to `glowbox/local_settings.py` (this Pi only, ignored by git, so `git pull` never conflicts). Run `camera_test.py` again to confirm. Delete `local_settings.py` to go back to the defaults in `hardware_config.py`.
   * If the photo is blurry, adjust `CAM_LENS_POSITION` (higher = focus closer).
   * Keep the cyan band **narrower** than the real line (`LINE_HALF_WIDTH_PX`), and keep lines a few mm away from the strip's ends.
   * The **orange** marks show where the line search starts and ends. `LINE_SEARCH = (0.20, 1.0)` skips the first 20% of the strip (the end pushed into the L-holder), because the holder's edge and shadow look like a line. Draw marker lines below the orange mark. If blank strips read well above 0.00, check the `roi` picture: the cyan band shows what is being mistaken for a line.
   * Optional: set `ROI` to a fixed `(top, bottom, left, right)` box and `LINE_ORIENTATION` to `"horizontal"`/`"vertical"` if the automatic finding ever picks the wrong area.
4. **Marker test:** type labels like `blue_1`, `blue_1/2`, `blue_1/4`, `blank` for each strip. Results go to `glowbox_data/bench.csv`, which you can open in Excel/Sheets to chart absorbance against dilution.
5. **Main program:** `python3 glowbox.py`
   * **Hold the button 3 s** → calibration. Insert a blank strip and press, 10 times (hold again to finish early after ≥3).
   * **Short press** → reads the strip. The LCD shows e.g. `A=0.142 POS` with the threshold and reading number, and **keeps showing it until the next press**, which starts the next reading. (Set `KEEP_RESULT_ON_LCD = False` to return to `GLOWBOX READY` after each reading.)

## 5. Optional: start automatically at power-on

A ready-made file is in `deploy/glowbox.service`, or create it by hand:

```bash
sudo nano /etc/systemd/system/glowbox.service
```

Paste this, replacing `youruser`:

```
[Unit]
Description=GlowBox reader
After=multi-user.target

[Service]
User=youruser
WorkingDirectory=/home/youruser/Absorbance/glowbox
ExecStart=/usr/bin/python3 /home/youruser/Absorbance/glowbox/glowbox.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then `sudo systemctl enable --now glowbox`. Stop it with `sudo systemctl stop glowbox` before running the other scripts, because only one program can use the camera at a time.

## Camera modes

`CAM_MODE` in `hardware_config.py`:
* `"auto"` (default): uses the raw sensor data if it works, otherwise falls back to the normal colour image and says so.
* `"raw"`: raw only. Most accurate, because the values are linear.
* `"rgb"`: the normal processed image only. Most robust, slightly less accurate.

Re-run calibration after changing modes: the numbers are not interchangeable.

## LCD messages

| LCD | Meaning |
|---|---|
| `GLOWBOX READY` | Waiting. Short press = read, hold 3 s = calibrate |
| `A=0.142 POS` | Absorbance above the calibrated threshold |
| `A=0.003 NEG` | Below the threshold |
| `A=... ?` / `NO CAL` | No calibration yet. Hold 3 s to calibrate |
| `TOO BRIGHT` / `TOO DARK` | Exposure needs adjusting (see step 4.3) |
| `NO STRIP` | No strip found: check it's under the camera and lit; aim the LEDs |
| `ERROR` | Something failed; the LEDs are switched off. Press to continue; details are printed in the terminal |
| `NO CAMERA` | Camera not detected: check the ribbon and `rpicam-hello --list-cameras` |

## Safety built in

* The excitation LEDs are off at start-up, turned off immediately after each capture, on any error, and on exit.
* A watchdog forces them off after `LED_MAX_ON_S` seconds no matter what.
* LCD pin 5 (R/W) **must** be wired to GND. Otherwise the LCD can push 5 V into the Pi's pins.

## When asking for help

Copy the full terminal output (especially lines starting with `ERROR` or `Traceback`) and the last lines of `glowbox_data/readings.csv` or `bench.csv`.
