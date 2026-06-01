from esp32.drivers import keypad
from esp32.config import CONFIG


KEY_MAP = {
    "A": "+",
    "B": "-",
    "C": "*",
    "D": "/",
    "*": "C",
    "#": "ENTER",
}


class InputManager:
    def __init__(self):
        self.expression = ""
        self._submit = False

    def read_key(self):
        key = keypad.scan_keypad()
        if key is None:
            return None

        if key == "#":
            self._submit = True
            return key

        if key == "*":
            self.expression = ""
            self._submit = False
            return key

        self._submit = False
        self.expression += KEY_MAP.get(key, key)
        return key

    def is_submit(self):
        return self._submit

    def reset(self):
        self.expression = ""
        self._submit = False
