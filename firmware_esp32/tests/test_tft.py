"""
test_tft.py — Visual + touch calibration test for the TFT. Requires hardware.
Tap the 4 screen corners: raw values are printed; use them for TOUCH X/Y_MIN/MAX
(after SWAP_XY). Usage: mpremote cp firmware_esp32/tests/test_tft.py :t.py && mpremote run t.py
"""
import sys, time
sys.path.insert(0, "/")
from config import CONFIG
from drivers.tft_display import TftDisplay, ACCENT, OK, DANGER, FG, BG
from drivers.touch_xpt2046 import TouchXpt2046

d = TftDisplay()
print("PASS  TftDisplay init", d.width, "x", d.height)
for i, c in enumerate((ACCENT, OK, DANGER, FG)):
    d.fill_rect(i * d.width // 4, 0, d.width // 4, 100, c)
d.draw_text("sqrt(x^2)<=5", 12, 120, 3, FG, BG, True)
d.draw_text("x>=0 y!=1", 12, 160, 2, FG, BG, True)
print("VISUAL: 4 color bars + glyph text")

t = TouchXpt2046(d.spi, d.width, d.height)
print("Touch test 15s: tap the corners")
end = time.ticks_add(time.ticks_ms(), 15000)
last = None
while time.ticks_diff(end, time.ticks_ms()) > 0:
    raw = t.read_raw()
    if raw and raw != last:
        print("raw", raw, "-> screen", t.read())
        last = raw
    if raw is None:
        last = None
    time.sleep_ms(30)