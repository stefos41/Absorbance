# Absorbance — GlowBox test-strip reader

A Raspberry Pi 4 + Camera Module 3 NoIR device that reads coloured test-strip lines under 650 nm red light and reports their **absorbance** and a POS/NEG verdict on a 1602 LCD.

* `glowbox/`: the code that runs on the Pi (setup and usage: [glowbox/README.md](glowbox/README.md))
* `docs/HARDWARE.md`: parts, pin map, wiring, safety checklist
* `deploy/glowbox.service`: optional auto-start at boot
* `tests/`: hardware-free simulations with fake GPIO and camera. Run `tests/run_all.sh` (needs `numpy` and `pillow`)

## Quick start on the Pi

```bash
git clone https://github.com/stefos41/Absorbance.git
cd Absorbance/glowbox
sudo apt install -y python3-picamera2 python3-gpiozero python3-lgpio python3-numpy python3-pil
python3 system_test.py     # wiring
python3 camera_test.py     # camera
python3 bench_measure.py   # set up exposure / ROI, marker tests
python3 glowbox.py         # the device
```

## Status

The code has been checked with simulated hardware only. Expect to tune exposure, ROI and focus (`glowbox/hardware_config.py`) on real hardware.
