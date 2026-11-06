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
      status      "OK", "TOO_DARK", "TOO_BRIGHT"
      absorbance  float (None if status is not OK)
      line_level, paper_level   mean brightness (above dark) of the line and of the paper
      line_pos    line position inside the ROI, 0.0 = start, 1.0 = end
      profile     1-D brightness profile across the ROI (for debugging/plots)
      line_index  index of the line centre in the profile
    """
    if sample.shape != dark.shape:
        raise ValueError("sample and dark images must be the same size")

    y0, y1, x0, x1 = roi_bounds(sample.shape, cfg.ROI)
    raw_roi = sample[y0:y1, x0:x1]
    roi = raw_roi - dark[y0:y1, x0:x1]

    result = {"status": "OK", "absorbance": None, "line_level": None,
              "paper_level": None, "line_pos": None, "profile": None,
              "line_index": None, "roi_px": (y0, y1, x0, x1)}

    # 1) Saturation check on the raw pixels (before dark subtraction)
    if float(raw_roi.max()) >= cfg.SATURATION_FRACTION * full_scale:
        result["status"] = "TOO_BRIGHT"
        return result

    # 2) Collapse the ROI into a 1-D profile ACROSS the line direction
    if cfg.LINE_ORIENTATION == "horizontal":
        profile = roi.mean(axis=1)     # one value per row
    elif cfg.LINE_ORIENTATION == "vertical":
        profile = roi.mean(axis=0)     # one value per column
    else:
        raise ValueError("LINE_ORIENTATION must be 'horizontal' or 'vertical'")
    profile = smooth(profile.astype(np.float64), cfg.SMOOTH_PX)
    result["profile"] = profile

    hw, gap, bgw = cfg.LINE_HALF_WIDTH_PX, cfg.BG_GAP_PX, cfg.BG_WIDTH_PX
    margin = hw + gap + bgw
    n = len(profile)
    if n < 2 * margin + 1:
        raise ValueError("ROI is too small for the line/background widths; enlarge ROI "
                         "or reduce LINE_HALF_WIDTH_PX / BG_GAP_PX / BG_WIDTH_PX")

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
