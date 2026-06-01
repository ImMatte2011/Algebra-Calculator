from machine import Pin, I2C
try:
    import ssd1306
except ImportError:
    ssd1306 = None

from esp32.config import CONFIG


class OLEDDisplay:
    def __init__(self):
        self.width = CONFIG["DISPLAY_WIDTH"]
        self.height = CONFIG["DISPLAY_HEIGHT"]
        self.i2c = I2C(0, scl=Pin(22), sda=Pin(21))
        if ssd1306 is None:
            raise ImportError("ssd1306 module is required for OLED display")
        self.display = ssd1306.SSD1306_I2C(self.width, self.height, self.i2c)

    def clear(self):
        self.display.fill(0)
        self.display.show()

    def draw_text(self, text: str, line: int = 0):
        self.clear()
        self.display.text(text, 0, line)
        self.display.show()
