"""Fake picamera2 for hardware-free tests. STATE controls the simulated scene."""
import numpy as np
__version__ = "fake"
STATE = {"led": None, "lag": 2, "since_on": 0, "raw_broken": False,
         "layout": "strip_vertical",   # or "strip_horizontal" (like a strip lying left-right)
         "glare": False, "paper": 400.0, "line_abs": 0.15,
         "ref_exposure": None, "controls": {}}   # ref_exposure: exposure*gain at which "paper" applies


def _scene(lit, h, w, black, scale):
    img = np.full((h, w), float(black))
    if lit:
        paper = STATE["paper"] * scale
        if STATE["ref_exposure"]:
            c = STATE["controls"]
            paper *= c.get("ExposureTime", 1) * c.get("AnalogueGain", 1) / STATE["ref_exposure"]
        if STATE["layout"] == "strip_vertical":          # tall strip, line runs left-right
            y0, y1, x0, x1 = int(.15*h), int(.85*h), int(.42*w), int(.58*w)
            img[y0:y1, x0:x1] += paper
            ly = int(.5*h)
            img[ly-4:ly+5, x0:x1] -= paper * (1 - 10 ** -STATE["line_abs"])
        else:                                            # wide strip, line runs up-down
            y0, y1, x0, x1 = int(.55*h), int(.75*h), int(.38*w), int(.76*w)
            img[y0:y1, x0:x1] += paper
            lx = int(.49*w)
            img[y0:y1, lx-4:lx+5] -= paper * (1 - 10 ** -STATE["line_abs"])
        img += paper * 0.02                              # a little stray light everywhere
        if STATE["glare"]:
            yy, xx = np.ogrid[:h, :w]
            img[(yy - int(.05*h))**2 + (xx - int(.6*w))**2 < (int(.05*h))**2] = black + 1000 * scale
    return img + np.random.normal(0, 2 * scale, img.shape)


class _Req:
    def __init__(self, cam):
        on = STATE["led"]() if STATE["led"] else False
        STATE["since_on"] = STATE["since_on"] + 1 if on else 0
        self.lit = on and STATE["since_on"] > STATE["lag"]

    def make_array(self, name):
        if name == "raw":
            if STATE["raw_broken"]:
                raise RuntimeError("raw stream unsupported (fake)")
            h, w = 1296, 2304
            raw16 = np.clip(_scene(self.lit, h, w, 64, 1.0), 0, 1023).astype(np.uint16)
            stride = np.zeros((h, w + 64), np.uint16)
            stride[:, :w] = raw16
            return stride.view(np.uint8)
        h, w = 648, 1152
        red = np.clip(_scene(self.lit, h, w, 0, 0.25), 0, 255).astype(np.uint8)
        arr = np.zeros((h, w, 3), np.uint8)
        arr[..., 2] = red
        arr[..., 1] = red // 3
        return arr

    def save(self, name, path):
        open(path, "wb").write(b"jpg")

    def release(self):
        pass


class Picamera2:
    sensor_modes = [{"size": (1536, 864), "unpacked": "SRGGB10", "bit_depth": 10},
                    {"size": (2304, 1296), "unpacked": "SRGGB10", "bit_depth": 10}]
    camera_controls = {k: 0 for k in ["AeEnable", "AwbEnable", "ExposureTime", "AnalogueGain",
                       "FrameDurationLimits", "AfMode", "LensPosition", "ColourGains"]}

    @staticmethod
    def global_camera_info():
        return [{"Model": "imx708_noir"}]

    def create_still_configuration(self, **kw):
        STATE["controls"] = dict(kw.get("controls", {}))
        return kw
    def configure(self, c): pass
    def start(self): pass
    def stop(self): pass
    def close(self): pass
    def capture_request(self): return _Req(self)
