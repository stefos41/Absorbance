"""
GlowBox - camera_reader.py
Camera Module 3 (NoIR) capture using picamera2, with the red LEDs switched around it.

Two modes (CAM_MODE in hardware_config.py):
  "raw"  - raw sensor data, red-filtered pixels only. Linear, most accurate.
  "rgb"  - the camera's normal processed colour image, red channel. Slightly less
           accurate (the image processing is not perfectly linear) but very robust.
  "auto" - try "raw"; if anything about it fails, fall back to "rgb" automatically.
Both modes give a red image of the same size (1152 x 648 by default).
"""
import threading
import time
import numpy as np


class LedWatchdog:
    """Forces the excitation LEDs off if they stay on too long (photobleaching / heat guard)."""

    def __init__(self, excite, max_on_s):
        self.excite = excite
        self.max_on_s = max_on_s
        self._timer = None

    def on(self):
        self.cancel()
        self._timer = threading.Timer(self.max_on_s, self.excite.off)
        self._timer.daemon = True
        self._timer.start()
        self.excite.on()

    def off(self):
        self.excite.off()
        self.cancel()

    def cancel(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None


class CameraReader:
    MAIN_SIZE = (1152, 648)    # same geometry as the red pixels of the 2304x1296 raw mode

    def __init__(self, cfg, excite, mode=None, verbose=False):
        from picamera2 import Picamera2   # imported here so other scripts work without a camera

        self.cfg = cfg
        self.verbose = verbose
        self.leds = LedWatchdog(excite, cfg.LED_MAX_ON_S)
        self.picam2 = Picamera2()
        self.fallback_reason = None

        wanted = (mode or getattr(cfg, "CAM_MODE", "auto")).lower()
        if wanted not in ("auto", "raw", "rgb"):
            raise ValueError("CAM_MODE must be 'auto', 'raw' or 'rgb'")

        if wanted in ("auto", "raw"):
            try:
                self._configure(use_raw=True)
                self._red_frame()                    # prove raw capture + decoding works
                return
            except Exception as e:
                if wanted == "raw":
                    raise
                self.fallback_reason = repr(e)
                self._log(f"raw mode failed ({e!r}); falling back to rgb mode")
                try:
                    self.picam2.stop()
                except Exception:
                    pass
        self._configure(use_raw=False)
        self._red_frame()

    # ---------------- setup ----------------
    def _log(self, msg):
        if self.verbose:
            print(f"[camera] {msg}")

    def _controls(self):
        cfg = self.cfg
        frame_us = max(cfg.CAM_EXPOSURE_US + 5000, 33_333)
        wanted = {
            "AeEnable": False,
            "AwbEnable": False,
            "ExposureTime": int(cfg.CAM_EXPOSURE_US),
            "AnalogueGain": float(cfg.CAM_GAIN),
            "FrameDurationLimits": (frame_us, frame_us),
            "AfMode": 0,                         # manual focus
            "LensPosition": float(cfg.CAM_LENS_POSITION),
            "ColourGains": (1.0, 1.0),           # fixed white balance (matters in rgb mode)
        }
        available = self.picam2.camera_controls
        return {k: v for k, v in wanted.items() if k in available}

    @staticmethod
    def _choose_mode(modes, wanted_size):
        for m in modes:
            if tuple(m["size"]) == tuple(wanted_size):
                return m
        modes = sorted(modes, key=lambda m: m["size"][0] * m["size"][1])
        for m in modes:
            if m["size"][0] >= wanted_size[0] and m["size"][1] >= wanted_size[1]:
                return m
        return modes[-1]

    def _configure(self, use_raw):
        self.use_raw = use_raw
        kwargs = dict(main={"size": self.MAIN_SIZE, "format": "RGB888"},
                      buffer_count=4, controls=self._controls())
        if use_raw:
            mode = self._choose_mode(self.picam2.sensor_modes, self.cfg.CAM_RAW_SIZE)
            raw_format = str(mode["unpacked"])          # e.g. "SRGGB10"
            self.bayer = raw_format[1:5]                # e.g. "RGGB"
            if sorted(self.bayer) != sorted("RGGB"):
                raise RuntimeError(f"unexpected Bayer pattern {self.bayer!r}")
            self.raw_width = mode["size"][0]
            self.full_scale = (1 << int(mode["bit_depth"])) - 1
            kwargs["raw"] = {"format": raw_format, "size": mode["size"]}
            self._log(f"raw mode: {raw_format} {mode['size']} bit_depth={mode['bit_depth']}")
        else:
            self.bayer = None
            self.full_scale = 255
            self._log(f"rgb mode: main {self.MAIN_SIZE}")
        config = self.picam2.create_still_configuration(**kwargs)
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(1.0)                                 # let the sensor settle

    @property
    def mode_name(self):
        return "raw" if self.use_raw else "rgb"

    # ---------------- frame decoding ----------------
    def _red_from_raw(self, raw):
        data = raw.view(np.uint16)[:, : self.raw_width]
        r, c = divmod(self.bayer.index("R"), 2)
        red = data[r::2, c::2].astype(np.float32)
        if float(red.max()) > self.full_scale:       # some platforms left-align the bits
            self.full_scale = 65535
        return red

    @staticmethod
    def _red_from_rgb(arr):
        # picamera2 "RGB888" arrays are stored B, G, R per pixel -> red is the last channel
        return arr[..., 2].astype(np.float32)

    def _red_frame(self, save_path=None):
        """Capture exactly one frame and return its red image."""
        req = self.picam2.capture_request()
        try:
            if self.use_raw:
                red = self._red_from_raw(req.make_array("raw"))
            else:
                red = self._red_from_rgb(req.make_array("main"))
            if save_path:
                req.save("main", save_path)
        finally:
            req.release()
        return red

    def _grab(self, n, save_path=None, flush=True):
        if flush:
            for _ in range(self.cfg.FLUSH_FRAMES):      # discard frames that began before the LED change
                self.picam2.capture_request().release()
        acc = None
        for k in range(n):
            red = self._red_frame(save_path if k == n - 1 else None)
            acc = red if acc is None else acc + red
        return acc / n

    # ---------------- public ----------------
    def measure(self, save_path=None):
        """Returns (sample, dark) red-channel images as float arrays."""
        self.leds.off()
        dark = self._grab(self.cfg.N_DARK_FRAMES)
        try:
            self.leds.on()
            time.sleep(self.cfg.LED_SETTLE_S)
            sample = self._grab(self.cfg.N_FRAMES, save_path)
        finally:
            self.leds.off()                              # LEDs off as soon as possible, always
        return sample, dark

    def close(self):
        self.leds.off()
        try:
            self.picam2.stop()
            self.picam2.close()
        except Exception:
            pass
