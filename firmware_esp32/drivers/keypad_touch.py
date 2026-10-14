"""
keypad_touch.py — Wraps any keypad and adds touch input.
A tap on a display zone emits its key sequence (e.g. ["2", ENTER]);
otherwise events come from the wrapped keypad.
"""
from drivers.keypad_base import KeypadBase


class TouchKeypadMux(KeypadBase):
    def __init__(self, keypad, display, touch):
        self._kp = keypad
        self._disp = display
        self._touch = touch
        self._queue = []
        self._was_down = False

    def update(self):
        if self._queue:
            return self._queue.pop(0)
        pos = self._touch.read()
        if pos is None:
            self._was_down = False
        elif not self._was_down:
            self._was_down = True
            for x, y, w, h, keys in self._disp.zones:
                if x <= pos[0] < x + w and y <= pos[1] < y + h:
                    self._queue.extend(keys[1:])
                    return keys[0]
        return self._kp.update()

    def reset_shift(self):
        self._kp.reset_shift()

    def __getattr__(self, name):          # is_ready(), is_connected(), ...
        return getattr(self._kp, name)