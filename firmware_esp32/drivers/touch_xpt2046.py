"""
touch_xpt2046.py — XPT2046 resistive touch on the SPI bus shared with the TFT.
read() returns (x, y) in screen pixels or None if not touched.
"""
from machine import Pin
from config import CONFIG


class TouchXpt2046:
    def __init__(self, spi, width, height):
        cfg = CONFIG["TOUCH"]
        self._spi = spi
        self._cs = Pin(cfg["CS_PIN"], Pin.OUT, value=1)
        self._irq = Pin(cfg["IRQ_PIN"], Pin.IN)
        self._baud = cfg.get("BAUDRATE", 2_000_000)
        self._restore = CONFIG["TFT"].get("BAUDRATE", 40_000_000)
        self._w, self._h = width, height
        self._swap = cfg.get("SWAP_XY", True)
        self._inv_x, self._inv_y = cfg.get("INVERT_X", False), cfg.get("INVERT_Y", False)
        self._xmin, self._xmax = cfg["X_MIN"], cfg["X_MAX"]
        self._ymin, self._ymax = cfg["Y_MIN"], cfg["Y_MAX"]

    def _xfer(self, cmd):
        buf = bytearray(3)
        self._spi.write_readinto(bytes((cmd, 0, 0)), buf)
        return ((buf[1] << 8) | buf[2]) >> 3

    def read_raw(self):
        """Median of 5 raw 12-bit samples (rx, ry) or None. Axis swap NOT applied."""
        if self._irq.value():
            return None
        xs, ys = [], []
        self._spi.init(baudrate=self._baud)
        self._cs.value(0)
        try:
            for _ in range(5):
                xs.append(self._xfer(0xD0))
                ys.append(self._xfer(0x90))
        finally:
            self._cs.value(1)
            self._spi.init(baudrate=self._restore)
        xs.sort()
        ys.sort()
        rx, ry = xs[2], ys[2]
        return None if rx < 50 or ry < 50 else (rx, ry)

    def read(self):
        raw = self.read_raw()
        if raw is None:
            return None
        rx, ry = raw
        if self._swap:
            rx, ry = ry, rx
        x = (rx - self._xmin) * self._w // (self._xmax - self._xmin)
        y = (ry - self._ymin) * self._h // (self._ymax - self._ymin)
        if self._inv_x:
            x = self._w - 1 - x
        if self._inv_y:
            y = self._h - 1 - y
        return max(0, min(self._w - 1, x)), max(0, min(self._h - 1, y))