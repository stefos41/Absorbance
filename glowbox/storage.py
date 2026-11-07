"""
GlowBox - storage.py
Calibration file, CSV logs and debug pictures.
"""
import csv
import json
import os
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def data_dir(cfg):
    path = os.path.join(HERE, cfg.DATA_DIR)
    os.makedirs(os.path.join(path, "photos"), exist_ok=True)
    return path


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def file_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def photo_path(cfg, prefix):
    if not cfg.SAVE_PHOTOS:
        return None
    return os.path.join(data_dir(cfg), "photos", f"{prefix}_{file_stamp()}.jpg")


def load_calibration(cfg):
    path = os.path.join(data_dir(cfg), cfg.CAL_FILE)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_calibration(cfg, cal):
    cal = dict(cal, timestamp=timestamp())
    with open(os.path.join(data_dir(cfg), cfg.CAL_FILE), "w") as f:
        json.dump(cal, f, indent=2)
    return cal


def append_csv(cfg, filename, row):
    """row: dict. Header is written the first time."""
    path = os.path.join(data_dir(cfg), filename)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)


def fmt(x, digits=4):
    return "" if x is None else f"{x:.{digits}f}"


def save_debug_image(cfg, red_image, result, path):
    """Grey picture of the red channel. Yellow = measuring box, cyan = line found,
    magenta = whole strip, red = other bright spots (e.g. an LED visible to the camera),
    orange = start/end of the line search."""
    from PIL import Image, ImageDraw

    img = np.asarray(red_image, dtype=np.float64)
    lo, hi = np.percentile(img, 1), np.percentile(img, 99.5)
    scaled = np.clip((img - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    pic = Image.fromarray(scaled).convert("RGB")
    draw = ImageDraw.Draw(pic)

    strip = result.get("strip")
    if strip:
        sy0, sy1, sx0, sx1 = strip["strip_px"]
        draw.rectangle([sx0, sy0, sx1 - 1, sy1 - 1], outline=(255, 0, 255), width=1)   # whole strip
        for oy0, oy1, ox0, ox1, _ in strip["others"]:
            draw.rectangle([ox0, oy0, ox1 - 1, oy1 - 1], outline=(255, 60, 60), width=2)  # other bright spots

    if result.get("roi_px") is None:
        pic.save(path)
        return
    y0, y1, x0, x1 = result["roi_px"]
    draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 220, 0), width=2)

    si = result.get("search_idx")
    if si:   # orange marks where the line search starts and ends
        for k in si:
            if result.get("orientation") == "horizontal":
                draw.line([x0, y0 + k, x1 - 1, y0 + k], fill=(255, 140, 0), width=1)
            else:
                draw.line([x0 + k, y0, x0 + k, y1 - 1], fill=(255, 140, 0), width=1)

    c = result.get("line_index")
    if c is not None:
        hw = cfg.LINE_HALF_WIDTH_PX
        if result.get("orientation") == "horizontal":
            draw.rectangle([x0, y0 + c - hw, x1 - 1, y0 + c + hw], outline=(0, 220, 255), width=1)
        else:
            draw.rectangle([x0 + c - hw, y0, x0 + c + hw, y1 - 1], outline=(0, 220, 255), width=1)
    pic.save(path)
