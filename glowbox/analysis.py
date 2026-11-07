"""
GlowBox - analysis.py
Pure-numpy absorbance analysis. No hardware needed, so it can be tested anywhere.

Idea: the camera photographs the strip under red light. A blue/purple/black line
absorbs red light, so it looks darker than the clean paper right next to it.
    absorbance = -log10( line brightness / paper brightness )
Both brightnesses have the DARK (LEDs off) image subtracted first.
Comparing the line with paper in the SAME photo cancels LED drift and strip placement.
"""
import math
import numpy as np


def roi_bounds(shape, roi):
    """Convert ROI fractions (top, bottom, left, right) into integer pixel bounds."""
    h, w = shape
    top, bottom, left, right = roi
    y0, y1 = int(round(top * h)), int(round(bottom * h))
    x0, x1 = int(round(left * w)), int(round(right * w))
    if not (0 <= y0 < y1 <= h and 0 <= x0 < x1 <= w):
        raise ValueError(f"ROI {roi} is invalid for image size {w}x{h}")
    return y0, y1, x0, x1


# ---------------- automatic strip finding ----------------
def _otsu_threshold(values):
    """Threshold that best splits values into a dark and a bright group."""
    hist, edges = np.histogram(values, bins=256)
    centres = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist).astype(float)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centres)
    mu0 = np.divide(m0, w0, out=np.zeros_like(m0), where=w0 > 0)
    mu1 = np.divide(m0[-1] - m0, w1, out=np.zeros_like(m0), where=w1 > 0)
    between = w0 * w1 * (mu0 - mu1) ** 2
    return float(centres[int(np.argmax(between))])


def _shift_or(mask, r):
    """Binary dilation by a (2r+1) square using array shifts."""
    out = mask.copy()
    h, w = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            ys, yd = (slice(dy, h), slice(0, h - dy)) if dy >= 0 else (slice(0, h + dy), slice(-dy, h))
            xs, xd = (slice(dx, w), slice(0, w - dx)) if dx >= 0 else (slice(0, w + dx), slice(-dx, w))
            out[yd, xd] |= mask[ys, xs]
    return out


def _close(mask, r):
    """Binary closing: fills gaps (like a dark line) up to ~2r cells wide."""
    dil = _shift_or(mask, r)
    return ~_shift_or(~dil, r)


def _components(mask):
    """Connected bright regions -> list of (area, y0, y1, x0, x1) in mask cells, largest first."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
    for sy, sx in zip(*np.nonzero(mask)):
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = True
        area, y0, y1, x0, x1 = 0, sy, sy, sx, sx
        while stack:
            y, x = stack.pop()
            area += 1
            y0, y1, x0, x1 = min(y0, y), max(y1, y), min(x0, x), max(x1, x)
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        comps.append((area, y0, y1 + 1, x0, x1 + 1))
    comps.sort(reverse=True)
    return comps


def find_strip(img, cfg):
    """
    Find the strip (the largest bright region) in a dark-subtracted image.
    Returns None if nothing bright enough, else a dict:
      roi_px       (y0, y1, x0, x1) measuring box inside the strip (edges trimmed)
      strip_px     (y0, y1, x0, x1) whole strip bounding box
      orientation  "vertical" if the strip lies left-right (so its lines run up-down), else "horizontal"
      others       list of (y0, y1, x0, x1, peak) for other bright spots (e.g. a visible LED)
    """
    f = 8                                              # work on an 8x smaller image (fast)
    h, w = img.shape
    hh, ww = h // f, w // f
    small = img[: hh * f, : ww * f].reshape(hh, f, ww, f).mean(axis=(1, 3))
    lo = float(np.percentile(small, 5))
    min_area = cfg.AUTO_MIN_AREA_FRAC * hh * ww
    ignore = np.zeros_like(small, dtype=bool)
    glare = []
    # Split bright from dark. If the bright part is only a small spot (an LED seen by the
    # camera), set that spot aside and split again, so a dim strip is still found.
    for _ in range(5):
        values = small[~ignore]
        if values.size < 10 or float(values.max()) - lo < cfg.AUTO_MIN_CONTRAST:
            return None
        t = _otsu_threshold(values)
        comps = _components(_close((small > t) & ~ignore, 3))   # closing bridges the dark line
        if comps and comps[0][0] >= min_area:
            break
        spot = small > t
        glare.extend(comps)
        ignore |= _shift_or(spot, 2)
    else:
        return None
    comps = comps[:1] + comps[1:] + glare

    _, y0, y1, x0, x1 = comps[0]
    sy0, sy1, sx0, sx1 = y0 * f, y1 * f, x0 * f, x1 * f
    sh, sw = sy1 - sy0, sx1 - sx0
    if cfg.LINE_ORIENTATION in ("horizontal", "vertical"):
        orientation = cfg.LINE_ORIENTATION
    else:
        orientation = "vertical" if sw > sh else "horizontal"

    # trim more across the strip (blurry long edges) than along it (keep lines near the ends)
    if orientation == "vertical":       # strip lies left-right: along = x, across = y
        my, mx = cfg.AUTO_MARGIN_ACROSS * sh, cfg.AUTO_MARGIN_ALONG * sw
    else:
        my, mx = cfg.AUTO_MARGIN_ALONG * sh, cfg.AUTO_MARGIN_ACROSS * sw
    roi = (int(sy0 + my), int(sy1 - my), int(sx0 + mx), int(sx1 - mx))

    others = []
    for area, oy0, oy1, ox0, ox1 in comps[1:]:
        if area >= 2:
            peak = float(img[oy0 * f:oy1 * f, ox0 * f:ox1 * f].max())
            others.append((oy0 * f, oy1 * f, ox0 * f, ox1 * f, peak))
    return {"roi_px": roi, "strip_px": (sy0, sy1, sx0, sx1),
            "orientation": orientation, "others": others}


def resolve_roi(sample, dark, cfg):
    """Return (roi_px, orientation, strip_info) for ROI = 'auto' or a fixed fraction tuple."""
    if isinstance(cfg.ROI, str) and cfg.ROI.lower() == "auto":
        info = find_strip(sample - dark, cfg)
        if info is None:
            return None, None, None
        return info["roi_px"], info["orientation"], info
    roi = roi_bounds(sample.shape, cfg.ROI)
    orientation = cfg.LINE_ORIENTATION if cfg.LINE_ORIENTATION in ("horizontal", "vertical") else "horizontal"
    return roi, orientation, None


def smooth(profile, k):
    if k <= 1:
        return profile
    kernel = np.ones(k) / k
    padded = np.pad(profile, (k // 2, k - 1 - k // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def analyze(sample, dark, cfg, full_scale):
    """
    sample, dark : 2-D float arrays (red-channel images, same size)
    cfg          : the hardware_config module
    full_scale   : maximum possible raw pixel value (e.g. 1023 for 10-bit)

    Returns a dict:
      status      "OK", "TOO_DARK", "TOO_BRIGHT", "NO_STRIP"
      absorbance  float (None if status is not OK)
      line_level, paper_level   mean brightness (above dark) of the line and of the paper
      line_pos    line position inside the ROI, 0.0 = start, 1.0 = end
      profile     1-D brightness profile across the ROI (for debugging/plots)
      line_index  index of the line centre in the profile
      roi_px, orientation, strip   where it measured and how (for debugging pictures)
    """
    if sample.shape != dark.shape:
        raise ValueError("sample and dark images must be the same size")

    result = {"status": "OK", "absorbance": None, "line_level": None,
              "paper_level": None, "line_pos": None, "profile": None,
              "line_index": None, "roi_px": None, "orientation": None, "strip": None}

    roi_px, orientation, strip = resolve_roi(sample, dark, cfg)
    if roi_px is None:
        result["status"] = "NO_STRIP"
        return result
    y0, y1, x0, x1 = roi_px
    result.update(roi_px=roi_px, orientation=orientation, strip=strip)
    raw_roi = sample[y0:y1, x0:x1]
    roi = raw_roi - dark[y0:y1, x0:x1]

    # 1) Saturation check on the raw pixels (before dark subtraction)
    if float(raw_roi.max()) >= cfg.SATURATION_FRACTION * full_scale:
        result["status"] = "TOO_BRIGHT"
        return result

    # 2) Collapse the ROI into a 1-D profile ACROSS the line direction
    if orientation == "horizontal":
        profile = roi.mean(axis=1)     # line runs left-right: one value per row
    else:
        profile = roi.mean(axis=0)     # line runs up-down: one value per column
    profile = smooth(profile.astype(np.float64), cfg.SMOOTH_PX)
    result["profile"] = profile

    hw, gap, bgw = cfg.LINE_HALF_WIDTH_PX, cfg.BG_GAP_PX, cfg.BG_WIDTH_PX
    margin = hw + gap + bgw
    n = len(profile)
    if n < 2 * margin + 1:
        result["status"] = "NO_STRIP"     # strip region too small to measure
        return result

    # 3) Paper brightness check
    paper_estimate = float(np.percentile(profile, 80))
    if paper_estimate < cfg.MIN_PAPER_LEVEL:
        result["status"] = "TOO_DARK"
        result["paper_level"] = paper_estimate
        return result

    # 4) Find the line: the position where the band is darkest RELATIVE TO the paper
    #    on both sides of it. Comparing locally ignores uneven lighting across the strip.
    cs = np.concatenate([[0.0], np.cumsum(profile)])

    def window_mean(start, length):          # mean of profile[start:start+length] for arrays of start
        return (cs[start + length] - cs[start]) / length

    centres = np.arange(margin, n - margin)
    line_means = window_mean(centres - hw, 2 * hw + 1)
    bg_means = 0.5 * (window_mean(centres - hw - gap - bgw, bgw)
                      + window_mean(centres + hw + gap + 1, bgw))
    ratio = np.maximum(line_means, 1e-6) / np.maximum(bg_means, 1e-6)
    best = int(np.argmin(ratio))
    c = int(centres[best])
    line_level = float(line_means[best])
    paper_level = float(bg_means[best])

    if paper_level < cfg.MIN_PAPER_LEVEL:
        result["status"] = "TOO_DARK"
        result["paper_level"] = paper_level
        return result

    absorbance = -math.log10(max(line_level, 1e-6) / paper_level)

    result.update(absorbance=absorbance, line_level=line_level, paper_level=paper_level,
                  line_pos=c / (n - 1), line_index=c)
    return result


def compute_threshold(blank_values, k_sigma, min_delta):
    """Threshold from blank-strip absorbances: mean + k*SD (at least mean + min_delta)."""
    vals = np.asarray(blank_values, dtype=float)
    if len(vals) < 3:
        raise ValueError("need at least 3 blank readings")
    mean = float(vals.mean())
    sd = float(vals.std(ddof=1))
    threshold = max(mean + k_sigma * sd, mean + min_delta)
    return {"blank_mean": mean, "blank_sd": sd, "threshold": threshold, "n": int(len(vals))}


def verdict(absorbance, calibration):
    """Return 'POS', 'NEG' or '?' (no calibration yet)."""
    if absorbance is None:
        return "?"
    if not calibration:
        return "?"
    return "POS" if absorbance > calibration["threshold"] else "NEG"
