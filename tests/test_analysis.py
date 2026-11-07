import os
HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, os.path.join(HERE, "..", "glowbox"))
import numpy as np
import hardware_config as cfg
import analysis

rng = np.random.default_rng(0)
H, W, FS, BLACK = 648, 1152, 1023, 64.0


def strip_image(line_abs, layout="tall", paper=500.0, line_frac=0.3, glare=False, grad=True, uneven=False):
    """Dark background, a bright strip, a dark line across it. Returns (sample, dark, truth)."""
    img = np.zeros((H, W))
    if layout == "tall":                                 # strip up-down, line left-right
        y0, y1, x0, x1 = int(.10*H), int(.90*H), int(.40*W), int(.60*W)
    else:                                                # strip left-right, line up-down
        y0, y1, x0, x1 = int(.55*H), int(.75*H), int(.30*W), int(.80*W)
    strip = np.full((y1 - y0, x1 - x0), float(paper))
    if grad:                                             # uneven lighting along the strip
        g = np.linspace(0.85, 1.15, strip.shape[0 if layout == "tall" else 1])
        strip *= g[:, None] if layout == "tall" else g[None, :]
    if uneven:                                           # bright ends, dim middle (LED hotspots)
        n = strip.shape[0 if layout == "tall" else 1]
        u = 0.4 + 0.6 * np.abs(np.linspace(-1, 1, n)) ** 1.5
        strip *= u[:, None] if layout == "tall" else u[None, :]
    if layout == "tall":
        c = int(line_frac * strip.shape[0]); strip[c-5:c+6, :] *= 10 ** -line_abs
    else:
        c = int(line_frac * strip.shape[1]); strip[:, c-5:c+6] *= 10 ** -line_abs
    img[y0:y1, x0:x1] = strip
    if glare:
        yy, xx = np.ogrid[:H, :W]
        img[(yy - 30)**2 + (xx - 950)**2 < 30**2] = 950      # LED seen near the top edge
    sample = img + BLACK + rng.normal(0, 3, (H, W))
    dark = BLACK + rng.normal(0, 3, (H, W))
    return np.clip(sample, 0, FS), dark


fails = 0
for layout in ("tall", "wide"):
    for glare in (False, True):
        print(f"--- {layout} strip, glare={glare}")
        for true in [0.0, 0.01, 0.05, 0.1, 0.3, 0.6]:
            r = analysis.analyze(*strip_image(true, layout, glare=glare), cfg, FS)
            want = "horizontal" if layout == "tall" else "vertical"
            ok = r["status"] == "OK" and r["orientation"] == want and (true == 0 or abs(r["absorbance"] - true) < 0.01 + 0.03 * true)
            fails += not ok
            print(f"true={true:.3f}  measured={r['absorbance'] if r['absorbance'] is None else round(r['absorbance'], 4)}"
                  f"  line runs {r['orientation']}  {r['status']}  {'ok' if ok else 'MISMATCH'}")

for layout in ("tall", "wide"):
    print(f"--- {layout} strip, uneven light + glare")
    for true in [0.0, 0.05, 0.3]:
        r = analysis.analyze(*strip_image(true, layout, glare=True, uneven=True, paper=600), cfg, FS)
        sp = r["strip"]["strip_px"] if r["strip"] else None
        whole = sp is not None and ((sp[1] - sp[0]) > 0.7 * H if layout == "tall" else (sp[3] - sp[2]) > 0.45 * W)
        ok = r["status"] == "OK" and whole and abs(r["absorbance"] - true) < 0.01 + 0.03 * true
        fails += not ok
        print(f"true={true:.3f} measured={r['absorbance'] if r['absorbance'] is None else round(r['absorbance'], 4)}"
              f" whole strip found={whole} {r['status']} {'ok' if ok else 'MISMATCH'}")

blanks = [analysis.analyze(*strip_image(0.0, "wide"), cfg, FS)["absorbance"] for _ in range(10)]
cal = analysis.compute_threshold(blanks, cfg.CAL_K_SIGMA, cfg.CAL_MIN_DELTA)
print("cal", {k: round(v, 4) if isinstance(v, float) else v for k, v in cal.items()})
v = [analysis.verdict(a, cal) for a in [0.0, 0.01, 0.03, 0.1]]
print("verdicts:", v); fails += v != ["NEG", "POS", "POS", "POS"]
st = analysis.analyze(*strip_image(0.1, paper=2000), cfg, FS)["status"]; print("bright:", st); fails += st != "TOO_BRIGHT"
st = analysis.analyze(*strip_image(0.1, paper=15), cfg, FS)["status"]; print("dim:", st); fails += st != "TOO_DARK"
st = analysis.analyze(*strip_image(0.1, paper=0), cfg, FS)["status"]; print("no strip:", st); fails += st != "NO_STRIP"

# fixed ROI mode still works
cfg.ROI, cfg.LINE_ORIENTATION = (0.12, 0.88, 0.45, 0.55), "horizontal"
r = analysis.analyze(*strip_image(0.2, "tall"), cfg, FS); print("fixed ROI:", round(r["absorbance"], 4)); fails += abs(r["absorbance"] - 0.2) > 0.02
print("ANALYSIS TESTS:", "PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
