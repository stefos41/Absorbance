# Prototype results (2026-11-06)

Data from the first working GlowBox prototype. Summary in the [main README](../README.md#results-prototype-2026-11-06).

| File | Contents |
|---|---|
| `readings.csv` | Device readings (`glowbox.py`): absorbance, POS/NEG, threshold |
| `bench.csv` | Setup and repeatability measurements (`bench_measure.py`) |
| `calibration.json` | Blank-strip calibration: mean, SD, threshold |
| `local_settings.py` | Tuned camera settings for this setup (copy to `glowbox/` on a new Pi to reuse) |

Test strips in `readings.csv`: reading 1 = blank, 2 = dark blue/black marker, 3 = faint marker, 4 = red marker.

Photos are kept off GitHub on purpose (they can show the surroundings). The device saves them on the Pi in `glowbox/glowbox_data/photos/`.
