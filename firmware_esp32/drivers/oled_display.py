"""
oled_display.py — OLED display driver for ESP32 (MicroPython).

Supports:
  Controller: SSD1309, SSD1306 (same command set), SH1106
  Interface: SPI (default for SSD1309) or I2C (for SSD1306)
  Resolution: 128×64 (configurable)

Everything is configurable in config.py → CONFIG["OLED"] without touching this file.
Extends DisplayBase for compatibility with the rest of the firmware.

Example SPI config (SSD1309, current hardware):
    "OLED": { "BUS": "SPI", "CONTROLLER": "SSD1309", "WIDTH": 128, "HEIGHT": 64,
              "SCK_PIN": 18, "MOSI_PIN": 23, "DC_PIN": 21, "CS_PIN": 5, "RST_PIN": 22 }

Example I2C config (SSD1306):
    "OLED": { "BUS": "I2C", "CONTROLLER": "SSD1306", "WIDTH": 128, "HEIGHT": 64,
              "SCL_PIN": 22, "SDA_PIN": 21, "I2C_ADDR": 0x3C }
"""

import time
import framebuf
from machine import Pin, SPI, I2C
from drivers.display_abstract import DisplayBase
from drivers.oled_glyphs import split_with_glyphs, GLYPH_WIDTH
from config import CONFIG

# ---------------------------------------------------------------------------
# SSD1306/SSD1309 initialization sequence
# ---------------------------------------------------------------------------
_INIT_SSD1306 = bytes([
    0xAE,         # display off
    0xD5, 0x80,   # set display clock div
    0xA8, 0x3F,   # set multiplex (63 = 64 righe)
    0xD3, 0x00,   # set display offset
    0x40,         # set start line = 0
    0x8D, 0x14,   # charge pump ON (per pannelli 3.3V)
    0x20, 0x00,   # memory addressing: horizontal
    0xA1,         # segment remap (col 127 → SEG0)
    0xC8,         # COM output scan direction: remapped
    0xDA, 0x12,   # COM pins hardware config
    0x81, 0xCF,   # set contrast
    0xD9, 0xF1,   # set pre-charge period
    0xDB, 0x40,   # set VCOMH deselect level
    0xA4,         # entire display ON (normal, follows RAM)
    0xA6,         # set normal display (not inverted)
    0xAF,         # display ON
])

# SH1106: similar to SSD1306 but uses page addressing with offset +2
_INIT_SH1106 = bytes([
    0xAE,
    0xD5, 0x80,
    0xA8, 0x3F,
    0xD3, 0x00,
    0x40,
    0xAD, 0x8B,   # charge pump (SH1106 ha il suo registro)
    0xA1,
    0xC8,
    0xDA, 0x12,
    0x81, 0xCF,
    0xD9, 0x1F,
    0xDB, 0x40,
    0xA4,
    0xA6,
    0xAF,
])


class OledDisplay(DisplayBase):
    """
    OLED display 128×64. Pixel-addressable, more flexible than the LCD.

    Available methods:
      clear()                   → clears the entire display
      show_text(text, line)     → text on a row (0 or 1 for 8px font, 0-7 for 8px font)
      show_text_large(text, y)  → 16px text at absolute y position (pixels)
      draw_pixel(x, y, color)   → turns a pixel on/off
      draw_hline(x, y, w)       → horizontal line
      draw_rect(x, y, w, h)     → rectangle
      fill_rect(x, y, w, h)     → filled rectangle
      show()                    → flushes the framebuffer to the display (required after draw_*)
      show_loading()            → startup screen
    """

    CHAR_W  = 8    # built-in font character width (pixels)
    CHAR_H  = 8    # built-in font character height (pixels)
    CHAR_W2 = 16   # large font (2×)
    CHAR_H2 = 16

    def __init__(self):
        cfg = CONFIG["OLED"]
        self.width  = cfg.get("WIDTH",  128)
        self.height = cfg.get("HEIGHT", 64)
        self._controller = cfg.get("CONTROLLER", "SSD1309").upper()
        self._bus_type   = cfg.get("BUS", "SPI").upper()

        # Framebuffer: MONO_VLSB is the format used by SSD1306/SSD1309/SH1106
        self._buf = bytearray(self.width * self.height // 8)
        self._fb  = framebuf.FrameBuffer(self._buf, self.width, self.height, framebuf.MONO_VLSB)

        if self._bus_type == "SPI":
            self._init_spi(cfg)
        else:
            self._init_i2c(cfg)

        self._send_init()
        self.clear()

    # -----------------------------------------------------------------------
    # Bus initialization
    # -----------------------------------------------------------------------
    def _init_spi(self, cfg):
        self._dc  = Pin(cfg["DC_PIN"],  Pin.OUT)
        self._cs  = Pin(cfg["CS_PIN"],  Pin.OUT)
        rst_pin   = cfg.get("RST_PIN", -1)
        self._rst = Pin(rst_pin, Pin.OUT) if rst_pin >= 0 else None

        self._spi = SPI(1,
            baudrate=8_000_000,
            polarity=0, phase=0,
            sck=Pin(cfg["SCK_PIN"]),
            mosi=Pin(cfg["MOSI_PIN"]),
        )
        self._cs.value(1)

        if self._rst:
            self._rst.value(1)
            time.sleep_ms(1)
            self._rst.value(0)
            time.sleep_ms(10)
            self._rst.value(1)
            time.sleep_ms(10)

        self._write_cmd  = self._write_cmd_spi
        self._write_data = self._write_data_spi

    def _init_i2c(self, cfg):
        self._i2c_addr = cfg.get("I2C_ADDR", 0x3C)
        self._i2c = I2C(0,
            scl=Pin(cfg["SCL_PIN"]),
            sda=Pin(cfg["SDA_PIN"]),
        )
        self._write_cmd  = self._write_cmd_i2c
        self._write_data = self._write_data_i2c

    # -----------------------------------------------------------------------
    # Low-level SPI write
    # -----------------------------------------------------------------------
    def _write_cmd_spi(self, cmd):
        self._dc.value(0)
        self._cs.value(0)
        self._spi.write(bytes([cmd]))
        self._cs.value(1)

    def _write_data_spi(self, data):
        self._dc.value(1)
        self._cs.value(0)
        self._spi.write(data)
        self._cs.value(1)

    # -----------------------------------------------------------------------
    # Low-level I2C write
    # -----------------------------------------------------------------------
    def _write_cmd_i2c(self, cmd):
        self._i2c.writeto(self._i2c_addr, bytes([0x00, cmd]))

    def _write_data_i2c(self, data):
        # Prefix 0x40 = co-bit=0, D/C=1 (data)
        buf = bytearray(len(data) + 1)
        buf[0] = 0x40
        buf[1:] = data
        self._i2c.writeto(self._i2c_addr, buf)

    # -----------------------------------------------------------------------
    # Controller init sequence
    # -----------------------------------------------------------------------
    def _send_init(self):
        seq = _INIT_SH1106 if self._controller == "SH1106" else _INIT_SSD1306
        for b in seq:
            self._write_cmd(b)

    # -----------------------------------------------------------------------
    # Flush framebuffer → display
    # SH1106 uses page addressing with column offset +2
    # -----------------------------------------------------------------------
    def show(self):
        if self._controller == "SH1106":
            offset = 2
            page_h = 8
            pages  = self.height // page_h
            for page in range(pages):
                self._write_cmd(0xB0 | page)
                self._write_cmd(0x00 | (offset & 0x0F))        # col low nibble
                self._write_cmd(0x10 | ((offset >> 4) & 0x0F)) # col high nibble
                start = page * self.width
                self._write_data(self._buf[start:start + self.width])
        else:
            # SSD1306/SSD1309: horizontal addressing → un unico trasferimento
            self._write_cmd(0x21)   # set column address
            self._write_cmd(0)
            self._write_cmd(self.width - 1)
            self._write_cmd(0x22)   # set page address
            self._write_cmd(0)
            self._write_cmd(self.height // 8 - 1)
            self._write_data(self._buf)

    # -----------------------------------------------------------------------
    # DisplayBase interface
    # -----------------------------------------------------------------------
    def clear(self):
        self._fb.fill(0)
        self.show()

    def show_text(self, text, line=0):
        """
        Writes text on a logical 8px row.
        line 0 = top row, line 7 = bottom row (for a 64px display).
        Only that row is overwritten; the rest of the buffer is left unchanged.
        """
        y = line * self.CHAR_H
        if y + self.CHAR_H > self.height:
            return
        # Clear only that row
        self._fb.fill_rect(0, y, self.width, self.CHAR_H, 0)
        # Truncate to the display width
        max_chars = self.width // self.CHAR_W
        self._fb.text(text[:max_chars], 0, y, 1)
        self.show()

    def show_loading(self):
        self._fb.fill(0)
        self._fb.text("Calc Algebraica", 0, 0, 1)
        self._fb.text("Loading...", 0, 16, 1)
        self.show()

    # -----------------------------------------------------------------------
    # Additional API (compared to LCD)
    # -----------------------------------------------------------------------
    def show_text_large(self, text, y=0):
        """
        16×16px text using two 8px font rows overlaid with 2× scaling.
        Simple scaling: each original row is drawn twice in height.
        """
        self._fb.fill_rect(0, y, self.width, self.CHAR_H2, 0)
        for i, char in enumerate(text):
            x = i * self.CHAR_W2
            if x + self.CHAR_W2 > self.width:
                break
            # Draw the character twice with a 1px offset → bold/large effect
            self._fb.text(char, x,     y,     1)
            self._fb.text(char, x + 1, y + 1, 1)
        self.show()

    def draw_pixel(self, x, y, color=1):
        self._fb.pixel(x, y, color)

    def draw_hline(self, x, y, width, color=1):
        self._fb.hline(x, y, width, color)

    def draw_vline(self, x, y, height, color=1):
        self._fb.vline(x, y, height, color)

    def draw_rect(self, x, y, w, h, color=1):
        self._fb.rect(x, y, w, h, color)

    def fill_rect(self, x, y, w, h, color=1):
        self._fb.fill_rect(x, y, w, h, color)

    def show_expr_and_status(self, expr_text, status_text=""):
        """
        Typical calculator layout:
        row 0-1: expression (possibly on 2 rows)
        row 7:   status / shift mode
        """
        self._fb.fill(0)
        max_chars = self.width // self.CHAR_W
        # Row 0: first N characters of the expression
        self._fb.text(expr_text[:max_chars], 0, 0, 1)
        # Row 1: expression overflow (if long)
        if len(expr_text) > max_chars:
            self._fb.text(expr_text[max_chars:max_chars*2], 0, 8, 1)
        # Row 7 (at the bottom): status
        if status_text:
            self._fb.fill_rect(0, self.height - 8, self.width, 8, 0)
            self._fb.text(status_text[:max_chars], 0, self.height - 8, 1)
        self.show()
    
    def _draw_glyph_bitmap(self, bitmap, x, y):
        """Draws an 8x8 bitmap (bytes, one byte per row) starting at (x,y)."""
        for row in range(8):
            byte = bitmap[row]
            for col in range(8):
                if byte & (0x80 >> col):
                    self._fb.pixel(x + col, y + row, 1)
 
    def show_text_glyphs(self, text, line=0):
        """
        Like show_text(), but replaces the known substrings (sqrt(, <=,
        >=, !=) with the corresponding bitmaps instead of printing them as text.
        The underlying expression (in InputHandler) remains unchanged: this
        method only affects rendering, not the data.
        """
        y = line * self.CHAR_H
        if y + self.CHAR_H > self.height:
            return
 
        self._fb.fill_rect(0, y, self.width, self.CHAR_H, 0)
 
        x = 0
        for content, kind in split_with_glyphs(text):
            if x >= self.width:
                break
            if kind == "glyph":
                self._draw_glyph_bitmap(content, x, y)
                x += GLYPH_WIDTH
            else:
                self._fb.text(content, x, y, 1)
                x += self.CHAR_W
        self.show()
 
    def show_expr_and_status_glyphs(self, expr_text, status_text=""):
        """Glyph variant of show_expr_and_status(). Use this to show the expression
        when you want mathematical symbols rendered as bitmaps instead of ASCII text
        (e.g. sqrt(, <=, >=, !=)."""
        self._fb.fill(0)
        max_chars = self.width // self.CHAR_W
 
        segments = split_with_glyphs(expr_text)
        x, y = 0, 0
        for content, kind in segments:
            w = GLYPH_WIDTH if kind == "glyph" else self.CHAR_W
            if x + w > self.width:
                x = 0
                y += self.CHAR_H
                if y + self.CHAR_H > self.height - self.CHAR_H:
                    break  # leave the last row free for the status
            if kind == "glyph":
                self._draw_glyph_bitmap(content, x, y)
            else:
                self._fb.text(content, x, y, 1)
            x += w
 
        if status_text:
            self._fb.fill_rect(0, self.height - 8, self.width, 8, 0)
            self._fb.text(status_text[:max_chars], 0, self.height - 8, 1)
 
        self.show()

    def invert(self, invert=True):
        """Inverts the display colors (useful for signaling errors)."""
        self._write_cmd(0xA7 if invert else 0xA6)

    def set_contrast(self, value):
        """Sets the brightness (0-255)."""
        self._write_cmd(0x81)
        self._write_cmd(value & 0xFF)

    def render(self, expr, cursor_pos, status="", result=None, is_menu=False,
               menu_top="", menu_bottom=""):
        if is_menu:
            self._fb.fill(0)
            self._fb.text("Type/Action:", 0, 0, 1)
            self._fb.text(menu_top, 0, 16, 1)
            self._fb.text(menu_bottom, 0, 24, 1)
            self._fb.text("CLR=cancel", 0, 56, 1)
            self.show()
        elif result is not None:
            self._fb.fill(0)
            self._fb.text("Result:", 0, 0, 1)
            self.show_text_large(result[:8], y=12)
            self._fb.text(result[8:], 0, 28, 1)
            self._fb.text(status, 0, 56, 1)
            self.show()
        else:
            if CONFIG["OLED"].get("USE_GLYPHS", True):
                self.show_expr_and_status_glyphs(expr, status)
            else:
                self.show_expr_and_status(expr, status)
