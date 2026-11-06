import numpy as np
STATE = {"led": None, "lag": 2, "since_on": 0, "raw_broken": False}
__version__ = "fake"
def _scene(lit, h, w, black):
    img = np.full((h, w), float(black))
    if lit:
        img += 400 * (1 if black else 0.5)
        img[h*600//1296:h*612//1296, :] *= 0.7
    return img + np.random.normal(0, 2, img.shape)
class _Req:
    def __init__(self, cam):
        on = STATE["led"]() if STATE["led"] else False
        STATE["since_on"] = STATE["since_on"] + 1 if on else 0
        self.lit = on and STATE["since_on"] > STATE["lag"]
    def make_array(self, name):
        if name == "raw":
            if STATE["raw_broken"]: raise RuntimeError("raw stream unsupported (fake)")
            h, w = 1296, 2304
            raw16 = np.clip(_scene(self.lit, h, w, 64), 0, 1023).astype(np.uint16)
            stride = np.zeros((h, w + 64), np.uint16); stride[:, :w] = raw16
            return stride.view(np.uint8)
        h, w = 648, 1152
        red = np.clip(_scene(self.lit, h, w, 0), 0, 255).astype(np.uint8)
        arr = np.zeros((h, w, 3), np.uint8); arr[..., 2] = red; arr[..., 1] = red // 3
        return arr
    def save(self, name, path): open(path, "wb").write(b"jpg")
    def release(self): pass
class Picamera2:
    sensor_modes = [{"size": (1536, 864), "unpacked": "SRGGB10", "bit_depth": 10},
                    {"size": (2304, 1296), "unpacked": "SRGGB10", "bit_depth": 10}]
    camera_controls = {k: 0 for k in ["AeEnable","AwbEnable","ExposureTime","AnalogueGain",
                       "FrameDurationLimits","AfMode","LensPosition","ColourGains"]}
    @staticmethod
    def global_camera_info(): return [{"Model": "imx708_noir"}]
    def create_still_configuration(self, **kw): return kw
    def configure(self, c): pass
    def start(self): pass
    def stop(self): pass
    def close(self): pass
    def capture_request(self): return _Req(self)
