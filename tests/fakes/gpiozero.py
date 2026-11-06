import collections, threading
LOG = []
PRESSES = collections.deque()   # list of 'short'/'long'
class DigitalOutputDevice:
    def __init__(self, pin, active_high=True, initial_value=False): self.pin=pin; self.value=int(initial_value)
    def on(self): self.value=1; LOG.append(("on", self.pin))
    def off(self): self.value=0; LOG.append(("off", self.pin))
    def close(self): pass
LED = DigitalOutputDevice
class Button:
    def __init__(self, pin, pull_up=True, bounce_time=None): self._held=0; self._t=None
    def wait_for_press(self, timeout=None):
        if not PRESSES: raise KeyboardInterrupt
        kind = PRESSES.popleft(); self._n = 1 if kind=="short" else 400
        return True
    @property
    def is_pressed(self):
        self._n -= 1; return self._n > 0
