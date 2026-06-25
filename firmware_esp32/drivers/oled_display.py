"""
oled_display.py — Driver display OLED per ESP32 (MicroPython).

Supporta:
  Controller: SSD1309, SSD1306 (stesso set di comandi), SH1106
  Interfaccia: SPI (default, per SSD1309) o I2C (per SSD1306)
  Risoluzione: 128×64 (configurabile)

Tutto configurabile in config.py → CONFIG["OLED"] senza toccare questo file.
Estende DisplayBase per compatibilità con il resto del firmware.

Esempio config SPI (SSD1309, hardware attuale):
    "OLED": { "BUS": "SPI", "CONTROLLER": "SSD1309", "WIDTH": 128, "HEIGHT": 64,
              "SCK_PIN": 18, "MOSI_PIN": 23, "DC_PIN": 21, "CS_PIN": 5, "RST_PIN": 22 }

Esempio config I2C (SSD1306):
    "OLED": { "BUS": "I2C", "CONTROLLER": "SSD1306", "WIDTH": 128, "HEIGHT": 64,
              "SCL_PIN": 22, "SDA_PIN": 21, "I2C_ADDR": 0x3C }
"""

import time
import framebuf
from machine import Pin, SPI, I2C
from drivers.display_abstract import DisplayBase
from config import CONFIG

# ---------------------------------------------------------------------------
# Sequenza di inizializzazione SSD1306/SSD1309
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
    0xA4,         # entire display ON (normal, segue RAM)
    0xA6,         # set normal display (non invertito)
    0xAF,         # display ON
])

# SH1106: simile a SSD1306 ma usa page addressing con offset +2
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
    Display OLED 128×64. Pixel-addressable, più flessibile dell'LCD.

    Metodi disponibili:
      clear()                   → cancella tutto il display
      show_text(text, line)     → testo su una riga (0 o 1 per font 8px, 0-7 per font 8px)
      show_text_large(text, y)  → testo 16px in posizione y assoluta (pixel)
      draw_pixel(x, y, color)   → accende/spegne un pixel
      draw_hline(x, y, w)       → linea orizzontale
      draw_rect(x, y, w, h)     → rettangolo
      fill_rect(x, y, w, h)     → rettangolo pieno
      show()                    → trasferisce il framebuffer al display (richiesto dopo draw_*)
      show_loading()            → schermata di avvio
    """

    CHAR_W  = 8    # larghezza carattere font built-in (pixel)
    CHAR_H  = 8    # altezza carattere font built-in
    CHAR_W2 = 16   # font grande (2×)
    CHAR_H2 = 16

    def __init__(self):
        cfg = CONFIG["OLED"]
        self.width  = cfg.get("WIDTH",  128)
        self.height = cfg.get("HEIGHT", 64)
        self._controller = cfg.get("CONTROLLER", "SSD1309").upper()
        self._bus_type   = cfg.get("BUS", "SPI").upper()

        # Framebuffer: MONO_VLSB è il formato usato da SSD1306/SSD1309/SH1106
        self._buf = bytearray(self.width * self.height // 8)
        self._fb  = framebuf.FrameBuffer(self._buf, self.width, self.height, framebuf.MONO_VLSB)

        if self._bus_type == "SPI":
            self._init_spi(cfg)
        else:
            self._init_i2c(cfg)

        self._send_init()
        self.clear()

    # -----------------------------------------------------------------------
    # Inizializzazione bus
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
    # Scrittura low-level SPI
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
    # Scrittura low-level I2C
    # -----------------------------------------------------------------------
    def _write_cmd_i2c(self, cmd):
        self._i2c.writeto(self._i2c_addr, bytes([0x00, cmd]))

    def _write_data_i2c(self, data):
        # Prefisso 0x40 = co-bit=0, D/C=1 (data)
        buf = bytearray(len(data) + 1)
        buf[0] = 0x40
        buf[1:] = data
        self._i2c.writeto(self._i2c_addr, buf)

    # -----------------------------------------------------------------------
    # Sequenza init controller
    # -----------------------------------------------------------------------
    def _send_init(self):
        seq = _INIT_SH1106 if self._controller == "SH1106" else _INIT_SSD1306
        for b in seq:
            self._write_cmd(b)

    # -----------------------------------------------------------------------
    # Flush framebuffer → display
    # SH1106 usa page addressing con offset colonna +2
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
        Scrive testo su una riga logica di 8px.
        line 0 = riga in cima, line 7 = riga in fondo (per display 64px).
        Sovrascrive solo quella riga, non tocca il resto del buffer.
        """
        y = line * self.CHAR_H
        if y + self.CHAR_H > self.height:
            return
        # Cancella solo la riga
        self._fb.fill_rect(0, y, self.width, self.CHAR_H, 0)
        # Tronca a larghezza display
        max_chars = self.width // self.CHAR_W
        self._fb.text(text[:max_chars], 0, y, 1)
        self.show()

    def show_loading(self):
        self._fb.fill(0)
        self._fb.text("Calc Algebraica", 0, 0, 1)
        self._fb.text("Loading...", 0, 16, 1)
        self.show()

    # -----------------------------------------------------------------------
    # API aggiuntiva (rispetto a LCD)
    # -----------------------------------------------------------------------
    def show_text_large(self, text, y=0):
        """
        Testo 16×16px usando due righe di font 8px sovrapposte con scaling 2×.
        Semplice scaling: ogni riga originale viene disegnata 2 volte in altezza.
        """
        self._fb.fill_rect(0, y, self.width, self.CHAR_H2, 0)
        for i, char in enumerate(text):
            x = i * self.CHAR_W2
            if x + self.CHAR_W2 > self.width:
                break
            # Disegna il carattere due volte con offset di 1px → effetto bold/large
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
        Layout tipico per la calcolatrice:
        riga 0-1: espressione (eventualmente su 2 righe)
        riga 7:   status / shift mode
        """
        self._fb.fill(0)
        max_chars = self.width // self.CHAR_W
        # Riga 0: primi N caratteri dell'espressione
        self._fb.text(expr_text[:max_chars], 0, 0, 1)
        # Riga 1: overflow dell'espressione (se lunga)
        if len(expr_text) > max_chars:
            self._fb.text(expr_text[max_chars:max_chars*2], 0, 8, 1)
        # Riga 7 (in fondo): status
        if status_text:
            self._fb.fill_rect(0, self.height - 8, self.width, 8, 0)
            self._fb.text(status_text[:max_chars], 0, self.height - 8, 1)
        self.show()

    def invert(self, invert=True):
        """Inverte i colori del display (utile per segnalare errori)."""
        self._write_cmd(0xA7 if invert else 0xA6)

    def set_contrast(self, value):
        """Imposta la luminosità (0-255)."""
        self._write_cmd(0x81)
        self._write_cmd(value & 0xFF)