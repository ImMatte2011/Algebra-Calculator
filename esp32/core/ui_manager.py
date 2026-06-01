from esp32.drivers.oled_display import OLEDDisplay
from esp32.utils.logger import logger


class UIManager:
    def __init__(self):
        self.display = OLEDDisplay()

    def show_message(self, message: str):
        logger.info(f"UI message: {message}")
        self.display.clear()
        self.display.draw_text(message)

    def update_expression(self, expression: str):
        self.display.clear()
        self.display.draw_text(expression)

    def show_result(self, result: str):
        self.display.clear()
        self.display.draw_text(result)
