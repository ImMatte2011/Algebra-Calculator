"""Calculator-side display proxy and touch-key input for a remote TFT ESP32."""

from config import CONFIG
from drivers.display_abstract import DisplayBase
from drivers.keypad_base import KeypadBase
from drivers.tft_link import TftUartLink


def _make_link():
    from machine import Pin, UART

    cfg = CONFIG["TFT_LINK"]
    uart = UART(
        cfg.get("UART_ID", 2),
        baudrate=cfg.get("BAUDRATE", 921600),
        tx=Pin(cfg["TX_PIN"]),
        rx=Pin(cfg["RX_PIN"]),
        rxbuf=2048,
        txbuf=2048,
        timeout=0,
    )
    return TftUartLink(uart)


class RemoteTftDisplay(DisplayBase):
    """DisplayBase implementation sending compact UI states, never pixel data."""

    def __init__(self, link=None):
        self.link = link if link is not None else _make_link()
        cfg = CONFIG["TFT"]
        rotation = cfg.get("ROTATION", 1)
        native_width = cfg.get("WIDTH", 320)
        native_height = cfg.get("HEIGHT", 480)
        self.width, self.height = (
            (native_height, native_width) if rotation in (1, 3)
            else (native_width, native_height)
        )
        self.cols = (self.width - 40) // 24
        self.rows = self.height // 16

    def clear(self):
        self.link.send({"t": "c"})

    def show_text(self, text, line=0):
        self.link.send({"t": "s", "v": str(text), "l": int(line)})

    def show_loading(self):
        self.link.send({"t": "l"})

    def render(self, expr, cursor_pos, status="", result=None, is_menu=False,
               menu_top="", menu_bottom=""):
        if result is not None and len(result) > 36:
            chars_per_line = (self.width - 40) // 16
            result = result[:chars_per_line * 6]
        self.link.send({
            "t": "r",
            "e": expr,
            "c": cursor_pos,
            "s": status,
            "v": result,
            "m": is_menu,
            "a": menu_top,
            "b": menu_bottom,
        })


class RemoteTouchKeypadMux(KeypadBase):
    """Combines local keypad input with touch keys sent by the TFT ESP32."""

    def __init__(self, keypad, link):
        self._kp = keypad
        self._link = link
        self._queue = []

    def update(self):
        while True:
            message = self._link.receive()
            if message is None:
                break
            if (isinstance(message, dict) and message.get("t") == "k"
                    and isinstance(message.get("v"), list)
                    and all(isinstance(key, str) for key in message["v"])):
                self._queue.extend(message["v"])
            else:
                print("TFT link: ignored unexpected input message")

        if self._queue:
            return self._queue.pop(0)
        return self._kp.update()

    def reset_shift(self):
        self._kp.reset_shift()

    def __getattr__(self, name):
        return getattr(self._kp, name)
