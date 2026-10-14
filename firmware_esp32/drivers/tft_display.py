"""
tft_display.py — ST7796 SPI TFT driver (320x480, RGB565) for ESP32 (MicroPython).

No full framebuffer (no PSRAM): text and rectangles are drawn straight to the
panel through SPI windows. Touch zones of the current screen are exposed in
`self.zones` as (x, y, w, h, [keys]) for TouchKeypadMux.
Config: CONFIG["TFT"] (see config.py).
"""
import time
import framebuf
from machine import Pin, SPI
from drivers.display_abstract import DisplayBase
from drivers.keypad_base import KeypadAction
from drivers.oled_glyphs import split_with_glyphs, GLYPHS, GLYPH_WIDTH
from config import CONFIG


def _c(r, g, b):
    return (((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)).to_bytes(2, "big")


BG     = _c(16, 18, 28)
PANEL  = _c(30, 34, 52)
BORDER = _c(70, 78, 110)
FG     = _c(235, 238, 250)
MUTED  = _c(130, 138, 165)
ACCENT = _c(90, 125, 255)
OK     = _c(50, 190, 120)
WARN   = _c(255, 190, 70)
DANGER = _c(220, 80, 90)

PAD = 12
GAP = 8

_MADCTL = {0: 0x48, 1: 0x28, 2: 0x88, 3: 0xE8}   # includes BGR bit (0x08)

_INIT = (
    (0x01, b"", 120),                       # software reset
    (0x11, b"", 120),                       # sleep out
    (0xF0, b"\xC3", 0), (0xF0, b"\x96", 0), # enable extended commands
    (0x3A, b"\x55", 0),                     # 16 bit/pixel
    (0xB4, b"\x01", 0),
    (0xB6, b"\x80\x02\x3B", 0),
    (0xE8, b"\x40\x8A\x00\x00\x29\x19\xA5\x33", 0),
    (0xC1, b"\x06", 0), (0xC2, b"\xA7", 0), (0xC5, b"\x18", 0),
    (0xE0, b"\xF0\x09\x0B\x06\x04\x15\x2F\x54\x42\x3C\x17\x14\x18\x1B", 0),
    (0xE1, b"\xE0\x09\x0B\x06\x04\x03\x2B\x43\x42\x3B\x16\x14\x17\x1B", 120),
    (0xF0, b"\x3C", 0), (0xF0, b"\x69", 120),  # disable extended commands
)

_NAMES = {"expr": "Expr.", "eq": "Equation", "ineq": "Inequal.",
          "simp": "Simplify", "expa": "Expand", "fact": "Factor"}
_ACTIONS = ("simp", "expa", "fact")
_GLEN = {id(b): len(p) for p, b in GLYPHS.items()}   # glyph → chars consumed

_cfb_buf = bytearray(8)
_cfb = framebuf.FrameBuffer(_cfb_buf, 8, 8, framebuf.MONO_HLSB)


class TftDisplay(DisplayBase):

    def __init__(self):
        cfg = CONFIG["TFT"]
        rot = cfg.get("ROTATION", 1)
        nat_w, nat_h = cfg.get("WIDTH", 320), cfg.get("HEIGHT", 480)
        self.width, self.height = (nat_h, nat_w) if rot in (1, 3) else (nat_w, nat_h)
        self._glyphs = cfg.get("USE_GLYPHS", True)
        self._es = 3                                   # expression font scale
        self.cols = (self.width - 2 * PAD - 16) // (8 * self._es)
        self.rows = self.height // 16
        self.zones = []
        self._screen = None
        self._menu = []
        self._menu_sig = ()

        self._dc = Pin(cfg["DC_PIN"], Pin.OUT, value=0)
        self._cs = Pin(cfg["CS_PIN"], Pin.OUT, value=1)
        self._bl = Pin(cfg["BL_PIN"], Pin.OUT, value=0)
        rst = cfg.get("RST_PIN", -1)
        self._rst = Pin(rst, Pin.OUT, value=1) if rst >= 0 else None
        self.spi = SPI(cfg.get("SPI_ID", 1), baudrate=cfg.get("BAUDRATE", 40_000_000),
                       polarity=0, phase=0, sck=Pin(cfg["SCK_PIN"]),
                       mosi=Pin(cfg["MOSI_PIN"]), miso=Pin(cfg["MISO_PIN"]))

        if self._rst:
            self._rst.value(0); time.sleep_ms(10)
            self._rst.value(1); time.sleep_ms(120)
        for cmd, data, delay in _INIT:
            self._cmd(cmd, data)
            if delay:
                time.sleep_ms(delay)
        madctl = _MADCTL[rot] if cfg.get("BGR", True) else _MADCTL[rot] & ~0x08
        self._cmd(0x36, bytes([madctl]))
        self._cmd(0x21 if cfg.get("INVERT", False) else 0x20)
        self._cmd(0x29)                                # display on
        self.clear()
        self._bl.value(1)

    # ------------------------------------------------------------------
    # Low level
    # ------------------------------------------------------------------
    def _cmd(self, cmd, data=b""):
        self._cs.value(0)
        self._dc.value(0)
        self.spi.write(bytes([cmd]))
        if data:
            self._dc.value(1)
            self.spi.write(data)
        self._cs.value(1)

    def _data(self, buf):
        self._cs.value(0)
        self._dc.value(1)
        self.spi.write(buf)
        self._cs.value(1)

    def _window(self, x0, y0, x1, y1):
        self._cmd(0x2A, bytes((x0 >> 8, x0 & 255, x1 >> 8, x1 & 255)))
        self._cmd(0x2B, bytes((y0 >> 8, y0 & 255, y1 >> 8, y1 & 255)))
        self._cmd(0x2C)

    def set_backlight(self, on=True):
        self._bl.value(1 if on else 0)

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------
    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.width, x + w), min(self.height, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        n = (x1 - x0) * (y1 - y0)
        chunk = min(n, 2048)
        buf = color * chunk
        mv = memoryview(buf)
        self._window(x0, y0, x1 - 1, y1 - 1)
        while n:
            k = min(n, chunk)
            self._data(buf if k == chunk else mv[:k * 2])
            n -= k

    def draw_rect(self, x, y, w, h, color, t=2):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    @staticmethod
    def _char_bitmap(ch):
        _cfb.fill(0)
        _cfb.text(ch, 0, 0, 1)
        return _cfb_buf

    def _blit8(self, bmp, x, y, s, fg, bg):
        """Draws an 8x8 MSB-first bitmap scaled by s."""
        w = 8 * s
        rowlen = w * 2
        fg_s, bg_s = fg * s, bg * s
        buf = bytearray(w * rowlen)
        for r in range(8):
            b = bmp[r]
            off = r * s * rowlen
            for c in range(8):
                buf[off + c * s * 2: off + (c + 1) * s * 2] = fg_s if b & (0x80 >> c) else bg_s
            for k in range(1, s):
                buf[off + k * rowlen: off + (k + 1) * rowlen] = buf[off:off + rowlen]
        self._window(x, y, x + w - 1, y + w - 1)
        self._data(buf)

    def draw_text(self, text, x, y, scale=2, fg=FG, bg=BG, glyphs=False, xmax=None):
        xmax = xmax or self.width
        cw = 8 * scale
        segs = split_with_glyphs(text) if glyphs else [(c, "char") for c in text]
        for content, kind in segs:
            if x + cw > xmax:
                break
            self._blit8(content if kind == "glyph" else self._char_bitmap(content),
                        x, y, scale, fg, bg)
            x += cw
        return x

    def _text_center(self, text, x, y, w, h, scale, fg, bg):
        tx = x + (w - len(text) * 8 * scale) // 2
        self.draw_text(text, tx, y + (h - 8 * scale) // 2, scale, fg, bg)

    def _button(self, x, y, w, h, label, fill, fg=FG, scale=2):
        self.fill_rect(x, y, w, h, fill)
        self.draw_rect(x, y, w, h, BORDER, 2)
        self._text_center(label, x, y, w, h, scale, fg, fill)

    def _cursor_x(self, text, col, x0, s):
        x, n = x0, 0
        segs = split_with_glyphs(text) if self._glyphs else [(c, "char") for c in text]
        for content, kind in segs:
            if n >= col:
                break
            n += _GLEN[id(content)] if kind == "glyph" else 1
            x += 8 * s
        return x

    # ------------------------------------------------------------------
    # DisplayBase interface
    # ------------------------------------------------------------------
    def clear(self):
        self.fill_rect(0, 0, self.width, self.height, BG)
        self._screen = None
        self.zones = []

    def show_text(self, text, line=0):
        y = 8 + line * 24
        if y + 16 > self.height:
            return
        self.fill_rect(0, y, self.width, 24, BG)
        self.draw_text(text, PAD, y, 2, FG, BG)

    def show_loading(self):
        self.clear()
        self.draw_text("Algebra", PAD, 90, 4, ACCENT, BG)
        self.draw_text("Calculator", PAD, 130, 4, FG, BG)
        self.draw_text("Loading...", PAD, 200, 2, MUTED, BG)

    def render(self, expr, cursor_pos, status="", result=None, is_menu=False,
               menu_top="", menu_bottom=""):
        if is_menu:
            self._render_menu(menu_top, menu_bottom)
        elif result is not None:
            self._render_result(expr, result, status)
        else:
            self._render_main(expr, cursor_pos, status)

    # ------------------------------------------------------------------
    # Screens
    # ------------------------------------------------------------------
    def _header(self, title, color=ACCENT):
        self.fill_rect(0, 0, self.width, 32, PANEL)
        self.draw_text(title, PAD, 8, 2, color, PANEL)

    def _render_main(self, expr, cursor_pos, status):
        W, H, s = self.width, self.height, self._es
        if self._screen != "main":
            self._screen = "main"
            self.fill_rect(0, 0, W, H, BG)
            self._header("Algebra Calc")
            tools = (("<", KeypadAction.LEFT, PANEL), (">", KeypadAction.RIGHT, PANEL),
                     ("DEL", KeypadAction.BACKSPACE, PANEL),
                     ("CLR", KeypadAction.CLEAR, DANGER), ("OK", KeypadAction.ENTER, ACCENT))
            bw = (W - 2 * PAD - 4 * GAP) // 5
            self.zones = []
            for i, (label, key, col) in enumerate(tools):
                x = PAD + i * (bw + GAP)
                self._button(x, H - 64, bw, 52, label, col)
                self.zones.append((x, H - 64, bw, 52, [key]))
        bx, by, bw, bh = PAD, 48, W - 2 * PAD, 72
        self.fill_rect(bx, by, bw, bh, PANEL)
        self.draw_rect(bx, by, bw, bh, BORDER, 2)
        tx, ty = bx + 8, by + (bh - 8 * s) // 2
        self.draw_text(expr, tx, ty, s, FG, PANEL, self._glyphs, bx + bw - 8)
        cx = self._cursor_x(expr, min(cursor_pos, self.cols - 1), tx, s)
        self.fill_rect(cx, ty + 8 * s + 2, 8 * s, 3, ACCENT)
        self.fill_rect(0, 136, W, 28, BG)
        if status:
            bad = status.startswith(("ERROR", "Timeout", "Phone"))
            self.draw_text(status[:W // 16 - 1], PAD, 140, 2, WARN if bad else MUTED, BG)

    def _render_menu(self, top, bottom):
        W, H = self.width, self.height
        found = [t.split("=", 1) for t in (top + " " + bottom).split()
                 if "=" in t and t[0].isdigit()]
        if found:
            self._menu = found                      # keep buttons on "Sel:x" / error redraws
        menu = self._menu
        sig = tuple(k for k, _ in menu)
        sel = bottom[4:] if bottom.startswith("Sel:") else None
        if self._screen != "menu" or sig != self._menu_sig:
            self._screen, self._menu_sig = "menu", sig
            self.fill_rect(0, 0, W, H, BG)
            self._header("Choose action" if menu and menu[0][1] in _ACTIONS else "Choose type")
            self._button(PAD, H - 64, W - 2 * PAD, 52, "CANCEL", DANGER)
        n, gap = len(menu), 12
        bw = (W - 2 * PAD - (n - 1) * gap) // n
        zones = [(PAD, H - 64, W - 2 * PAD, 52, [KeypadAction.CLEAR])]
        for i, (k, label) in enumerate(menu):
            x = PAD + i * (bw + gap)
            self._button(x, 64, bw, 130, _NAMES.get(label, label),
                         ACCENT if k == sel else PANEL)
            self.draw_text(k, x + 8, 72, 2, MUTED, ACCENT if k == sel else PANEL)
            zones.append((x, 64, bw, 130, [k, KeypadAction.ENTER]))
        self.zones = zones
        self.fill_rect(0, 210, W, 28, BG)
        if bottom and "=" not in bottom and sel is None:
            self.draw_text(bottom[:W // 16 - 1], PAD, 214, 2, WARN, BG)

    def _render_result(self, expr, result, status):
        W, H = self.width, self.height
        self._screen, self.zones = "result", []
        self.fill_rect(0, 0, W, H, BG)
        self._header("Result", OK)
        self.draw_text(expr.strip(), PAD, 44, 2, MUTED, BG, self._glyphs, W - PAD)
        s = 3 if len(result) <= 36 else 2
        n = (W - 2 * PAD - 16) // (8 * s)
        lines = [result[i:i + n] for i in range(0, len(result), n)][:6]
        ch = len(lines) * (8 * s + 8) + 16
        self.fill_rect(PAD, 80, W - 2 * PAD, ch, PANEL)
        self.draw_rect(PAD, 80, W - 2 * PAD, ch, OK, 2)
        for i, line in enumerate(lines):
            self.draw_text(line, PAD + 8, 88 + i * (8 * s + 8), s, FG, PANEL)
        if status:
            self.draw_text(status[:W // 16 - 1], PAD, H - 28, 2, MUTED, BG)