# GlowBox hardware reference (v1.2, absorbance)

GlowBox lights a test strip with 650 nm red LEDs, photographs it with a Raspberry Pi Camera Module 3, and reports the line's absorbance (how much darker the line is than the paper beside it) plus a POS/NEG verdict on a 16x2 LCD. No optical filter is used.

## Bill of materials

| Item | Spec | Qty | Role |
|---|---|---|---|
| Raspberry Pi 4 Model B | 4 GB, Raspberry Pi OS 64-bit | 1 | Main computer |
| Raspberry Pi 1 Model B+ | same 40-pin header | 1 | Optional GPIO test bench (no camera work) |
| Pi Camera Module 3 | IMX708, standard or NoIR (the prototype reports `imx708`, i.e. standard); 15-pin 1 mm ribbon (included) | 1 | Imaging |
| Red LED | 650 nm, 5 mm, diffused with paper/tissue | 1–5 (prototype: 1) | Strip illumination |
| N-channel MOSFET | **IRLZ44N** (not IRFZ44N) | 1 | Low-side LED switch |
| Resistors | 150 Ω ×5, 220 Ω ×2, 330 Ω ×1, 10 kΩ ×1, 100 Ω ×1 | | See below |
| Status LEDs | standard red + standard green (Vf ≈ 2 V) | 2 | Ready / result / error |
| Tactile button | 4-leg | 1 | Read / hold 3 s calibrate / hold 10 s shut down |
| 1602A LCD | 16-pin, HD44780, no I²C backpack | 1 | Display |
| Potentiometer | 10 kΩ | 1 | LCD contrast |
| Power | 5.1 V / 3 A USB-C | 1 | Pi 4 + LED rail |
| Enclosure | 15×15×15 cm, matte black; L-shaped strip holder (strip pushed into the corner) | 1 | Light-tight chamber |

## Power and ground

* The Pi is powered **only** through USB-C. Never feed 5 V into the header from another supply.
* Breadboard + rail = Pi 5 V (physical pin 2 or 4). Feeds the red LEDs and LCD.
* Breadboard − rail = Pi GND (physical pin 6). **Mandatory shared ground.**
* `vcgencmd get_throttled` must print `throttled=0x0`.

## GPIO pin map

| Signal | BCM | Physical | Dir | Active | Connects to |
|---|---|---|---|---|---|
| EXCITE (LED switch) | 17 | 11 | out | HIGH = LEDs on | 330 Ω → MOSFET gate |
| BUTTON | 27 | 13 | in, pull-up | LOW = pressed | button → GND |
| GREEN status | 22 | 15 | out | HIGH | 220 Ω → green LED → GND |
| RED status | 23 | 16 | out | HIGH | 220 Ω → red LED → GND |
| LCD RS | 5 | 29 | out | | LCD pin 4 |
| LCD E | 6 | 31 | out | | LCD pin 6 |
| LCD D4 | 12 | 32 | out | | LCD pin 11 |
| LCD D5 | 13 | 33 | out | | LCD pin 12 |
| LCD D6 | 19 | 35 | out | | LCD pin 13 |
| LCD D7 | 26 | 37 | out | | LCD pin 14 |
| 5 V | | 2 / 4 | power | | + rail |
| GND | | 6 | power | | − rail |
| Camera | | CAMERA port | | | ribbon, contacts toward HDMI |

## Red LED bank and MOSFET

Each LED: 5 V rail → 150 Ω → LED anode (long leg) → cathode → MOSFET drain → source → GND. About 20 mA per LED.

| IRLZ44N pin (label facing you, L→R) | Connect to |
|---|---|
| Gate | 330 Ω to GPIO17; 10 kΩ to GND |
| Drain (and metal tab) | all LED cathodes |
| Source | GND rail |

One resistor per LED, LEDs in parallel.

## Status LEDs and button

* Green: GPIO22 → 220 Ω → LED → GND. Red: GPIO23 → 220 Ω → LED → GND.
* Button: diagonal legs, one to GPIO27, the other to GND. Never to 3.3 V or 5 V.

## 1602 LCD

| LCD pin | Name | Connect to |
|---|---|---|
| 1 | VSS | GND |
| 2 | VDD | 5 V |
| 3 | V0 | 10 kΩ pot wiper (outer legs to 5 V and GND) |
| 4 | RS | GPIO5 |
| 5 | R/W | **GND (mandatory)** |
| 6 | E | GPIO6 |
| 7–10 | D0–D3 | not connected |
| 11–14 | D4–D7 | GPIO12, 13, 19, 26 |
| 15 | A | 100 Ω → 5 V |
| 16 | K | GND |

## Optics and enclosure

* Prototype setup: one 650 nm LED, diffused, angled at the strip; camera ~15 cm above; strip pushed into an L-shaped cardboard holder. The code skips the first 20% of the strip at the holder end because the holder's edge and shadow look like a line.
* Reflection geometry: LEDs on two or more walls at 45° pointing at the strip; camera centred in the ceiling ~15 cm above the strip, pointing down.
* No LED visible from the lens; matte black interior; strip in a fixed holder; cable entries light-trapped.
* Red 650 nm LEDs read blue/purple/black lines. Red/pink (gold) lines would need green ~525 nm LEDs.

## Pre-power-up checklist

- [ ] No 5 V wire touches any GPIO row (multimeter continuity check)
- [ ] Pi GND bonded to the − rail
- [ ] MOSFET is IRLZ44N, G-D-S in separate rows, 10 kΩ gate pull-down fitted
- [ ] Every LED has its own resistor
- [ ] Button only between GPIO27 and GND
- [ ] LCD R/W to GND before any data wire
- [ ] Camera ribbon seated with the Pi off
- [ ] Run `system_test.py` first
