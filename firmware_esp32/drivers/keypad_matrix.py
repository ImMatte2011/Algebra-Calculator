import time
from machine import Pin
from config import CONFIG
from drivers.keypad_base import KeypadBase, KeypadAction

class KeypadMatrix(KeypadBase):
    """Astrazione del tastierino matriciale con modalità SHIFT_A / SHIFT_B e debounce."""

    DEFAULT_KEY_MATRIX = [
        ["K_1", "K_2", "K_3", "K_SHIFT"],
        ["K_4", "K_5", "K_6", "K_BACKSPACE"],
        ["K_7", "K_8", "K_9", "K_DELETE"],
        ["K_STAR", "K_0", "K_POUND", "K_ENTER"],
    ]

    def __init__(self, row_pins, col_pins, key_matrix=None, primary_map=None, shift_a_map=None, shift_b_map=None):
        self.rows = [Pin(pin, Pin.OUT) for pin in row_pins]
        self.cols = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in col_pins]
        self.key_matrix = key_matrix or self.DEFAULT_KEY_MATRIX
        
        # Carica le mappe passate o quelle da config.py
        keypad_cfg = CONFIG.get("KEYPAD", {})
        self.primary_map = primary_map or keypad_cfg.get("PRIMARY_MAP")
        self.shift_a_map = shift_a_map or keypad_cfg.get("SHIFT_A_MAP")
        self.shift_b_map = shift_b_map or keypad_cfg.get("SHIFT_B_MAP")
        
        self.shift_mode = None  # Può essere: None, "A", "B"
        self.debounce_ms = CONFIG.get("KEY_DEBOUNCE_MS", 50)
        self._last_raw = None
        self._last_time = time.ticks_ms()
        self._stable_key = None

        for row in self.rows:
            row.value(1)

    def _scan_raw(self):
        for r_index, row_pin in enumerate(self.rows):
            row_pin.value(0)
            for c_index, col_pin in enumerate(self.cols):
                if col_pin.value() == 0:
                    row_pin.value(1)
                    return self.key_matrix[r_index][c_index]
            row_pin.value(1)
        return None

    def update(self):
        """Restituisce una chiave stabile dopo il debounce, oppure None."""
        raw_key = self._scan_raw()
        current_time = time.ticks_ms()

        if raw_key == self._last_raw:
            if raw_key is not None and self._stable_key is None:
                elapsed = time.ticks_diff(current_time, self._last_time)
                if elapsed >= self.debounce_ms:
                    self._stable_key = raw_key
        else:
            self._last_raw = raw_key
            self._last_time = current_time
            self._stable_key = None

        if self._stable_key is not None:
            key = self._stable_key
            self._stable_key = None
            return self._translate_key(key)

        return None

    def _translate_key(self, physical_key):
        """Traduce il tasto fisico in un valore o un comando interno in base al doppio Shift."""
        if self.shift_mode == "A":
            mapped = self.shift_a_map.get(physical_key)
        elif self.shift_mode == "B":
            mapped = self.shift_b_map.get(physical_key)
        else:
            mapped = self.primary_map.get(physical_key)

        if mapped is None:
            return None

        # Gestione atomica del cambio stato dei due SHIFT
        if mapped == "CMD_SHIFT_A":
            self.shift_mode = None if self.shift_mode == "A" else "A"
            return KeypadAction.SHIFT_A
        elif mapped == "CMD_SHIFT_B":
            self.shift_mode = None if self.shift_mode == "B" else "B"
            return KeypadAction.SHIFT_B

        # Mappatura dei comandi standard CMD_ ai relativi KeypadAction
        cmd_map = {
            "CMD_ENTER": KeypadAction.ENTER,
            "CMD_BACKSPACE": KeypadAction.BACKSPACE,
            "CMD_DELETE": KeypadAction.DELETE,
            "CMD_SHIFT": KeypadAction.SHIFT,
            "CMD_CLEAR": KeypadAction.CLEAR,
            "CMD_LEFT": KeypadAction.LEFT,
            "CMD_RIGHT": KeypadAction.RIGHT,
            "CMD_UP": KeypadAction.UP,
            "CMD_DOWN": KeypadAction.DOWN,
        }

        if mapped in cmd_map:
            return cmd_map[mapped]

        # Altrimenti restituisce il carattere testuale ('x', '(', '+', ecc.)
        return mapped

    def reset_shift(self):
        self.shift_mode = None

    def get_active_map(self):
        if self.shift_mode == "A":
            return self.shift_a_map
        if self.shift_mode == "B":
            return self.shift_b_map
        return self.primary_map