"""Standalone entry point for the ESP32 that owns the ST7796 TFT and touch."""

import time
from config import CONFIG
from drivers.tft_display import TftDisplay
from drivers.touch_xpt2046 import TouchXpt2046
from drivers.tft_remote_display import _make_link


def _handle_message(display, message):
    if not isinstance(message, dict):
        print("TFT link: ignored non-object command")
        return

    kind = message.get("t")
    if kind == "c":
        display.clear()
    elif kind == "l":
        display.show_loading()
    elif kind == "s":
        text, line = message.get("v"), message.get("l")
        if not isinstance(text, str) or not isinstance(line, int):
            print("TFT link: ignored invalid text command")
            return
        display.show_text(text, line)
    elif kind == "r":
        expr, cursor = message.get("e"), message.get("c")
        status, result = message.get("s"), message.get("v")
        menu, top, bottom = message.get("m"), message.get("a"), message.get("b")
        if (not isinstance(expr, str) or not isinstance(cursor, int)
                or not isinstance(status, str)
                or (result is not None and not isinstance(result, str))
                or not isinstance(menu, bool)
                or not isinstance(top, str) or not isinstance(bottom, str)):
            print("TFT link: ignored invalid render command")
            return
        display.render(expr, cursor, status, result, menu, top, bottom)
    else:
        print("TFT link: ignored unknown command", kind)


def run():
    display = TftDisplay()
    touch_cfg = CONFIG.get("TOUCH", {})
    touch = (TouchXpt2046(display.spi, display.width, display.height)
             if touch_cfg.get("ENABLED", True) else None)
    link = _make_link()
    display.show_loading()
    was_down = False

    while True:
        message = link.receive()
        if message is not None:
            _handle_message(display, message)

        if touch is not None:
            pos = touch.read()
            if pos is None:
                was_down = False
            elif not was_down:
                was_down = True
                for x, y, w, h, keys in display.zones:
                    if x <= pos[0] < x + w and y <= pos[1] < y + h:
                        link.send({"t": "k", "v": keys})
                        break
        time.sleep_ms(5)


if __name__ == "__main__":
    run()
