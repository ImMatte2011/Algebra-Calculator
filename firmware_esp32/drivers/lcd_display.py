from machine import Pin, I2C

try:
    from drivers.i2c_lcd import I2cLcd
except ImportError:
    I2cLcd = None

from drivers.display_abstract import DisplayBase


class LCDDisplay(DisplayBase):
    """I2C LCD display with a standardized interface."""

    DEFAULT_I2C_ID = 0
    DEFAULT_I2C_ADDR = 0x27
    DEFAULT_COLS = 16
    DEFAULT_ROWS = 2

    def __init__(
        self,
        scl_pin: int = 22,
        sda_pin: int = 21,
        i2c_id: int = DEFAULT_I2C_ID,
        i2c_addr: int = DEFAULT_I2C_ADDR,
        cols: int = DEFAULT_COLS,
        rows: int = DEFAULT_ROWS,
    ):
        if I2cLcd is None:
            raise ImportError("The i2c_lcd module is not available. Install the I2C LCD driver")

        self.cols = cols
        self.rows = rows
        self.i2c = I2C(i2c_id, scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.lcd = I2cLcd(self.i2c, i2c_addr, rows, cols)
        
        # --- SAFETY ADDITION FOR THE BASE API ---
        # Inject the missing names directly into the created instance
        # so lcd_api.py (line 45) does not complain about 'num_columns'
        self.lcd.num_columns = cols
        self.lcd.num_lines = rows
        # -----------------------------------------------
        
        self.clear()

    def clear(self):
        self.lcd.clear()

    def show_text(self, text: str, line: int = 0):
        if not (0 <= line < self.rows):
            raise ValueError("line must be between 0 and rows-1")

        self.lcd.move_to(0, line)
        padded = (text + " " * (self.cols - len(text)))[: self.cols]
        self.lcd.putstr(padded)

    def blink_cursor_on(self):
        if hasattr(self.lcd, "blink_cursor_on"):
            self.lcd.blink_cursor_on()

    def set_cursor(self, x: int, y: int = 0):
        if not (0 <= x < self.cols) or not (0 <= y < self.rows):
            return
        self.lcd.move_to(x, y)

    def show_loading(self):
        self.clear()
        self.show_text("Loading...", 0)
        if self.rows > 1:
            self.show_text("Please wait", 1)

    def render(self, expr, cursor_pos, status="", result=None, is_menu=False,
               menu_top="", menu_bottom=""):
        if is_menu:
            self.show_text(menu_top, 0)
            self.show_text(menu_bottom, 1)
        elif result is not None:
            self.show_text("Result:", 0)
            self.show_text(result[:self.cols], 1)
        else:
            self.show_text(expr[:self.cols], 0)
            self.show_text(status[:self.cols], 1)
