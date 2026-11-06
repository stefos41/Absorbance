import os
HERE = os.path.dirname(os.path.abspath(__file__))
import sys, types, numpy as np
sys.path.insert(0, os.path.join(HERE, "..", "glowbox"))
import hardware_config as cfg, analysis

rng = np.random.default_rng(0)
H, W = 648, 1152
FS = 1023
def make(line_abs, pos=0.5, paper=500.0, black=64.0, noise=3.0, grad=True):
    img = np.full((H, W), float(paper))
    if grad:  # uneven lighting
        img *= np.linspace(0.85, 1.15, H)[:, None]
    y0, y1, _, _ = analysis.roi_bounds((H, W), cfg.ROI)
    c = int(y0 + pos * (y1 - y0))
    img[c-5:c+6, :] *= 10 ** (-line_abs)
    sample = img + black + rng.normal(0, noise, (H, W))
    dark = black + rng.normal(0, noise, (H, W))
    return sample, dark

for true in [0.0, 0.01, 0.05, 0.1, 0.3, 0.6]:
    s, d = make(true, pos=0.3)
    r = analysis.analyze(s, d, cfg, FS)
    print(f"true={true:.3f}  measured={r['absorbance']:.4f}  pos={r['line_pos']:.2f} {r['status']}")

blanks = [analysis.analyze(*make(0.0), cfg, FS)["absorbance"] for _ in range(10)]
cal = analysis.compute_threshold(blanks, cfg.CAL_K_SIGMA, cfg.CAL_MIN_DELTA)
print("cal", cal)
print("verdicts:", [analysis.verdict(a, cal) for a in [0.0, 0.01, 0.03, 0.1]])
s, d = make(0.1, paper=2000); print("bright:", analysis.analyze(s, d, cfg, FS)["status"])
s, d = make(0.1, paper=10); print("dark:", analysis.analyze(s, d, cfg, FS)["status"])
