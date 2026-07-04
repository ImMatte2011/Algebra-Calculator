"""
keypad_base.py — Abstract interface for the keypad.

Defines KeypadAction (the logical commands recognized by InputHandler)
and KeypadBase (the abstract base class that each hardware implementation must
extend). The code in main.py and input_handler.py depends only on these two,
never on the concrete drivers.
"""


class KeypadAction:
    """Logical commands produced by the keypad, independent of hardware."""
    ENTER     = "ENTER"
    BACKSPACE = "BACKSPACE"
    DELETE    = "DELETE"
    CLEAR     = "CLEAR"
    LEFT      = "LEFT"
    RIGHT     = "RIGHT"
    UP        = "UP"
    DOWN      = "DOWN"

    # Layer-based actions (F13-F18 on BLE macropad, or dedicated keys on matrix keypad)
    ACTION_SIMPLIFY  = "CMD_SIMPLIFY"
    ACTION_EXPAND    = "CMD_EXPAND"
    ACTION_FACTOR    = "CMD_FACTOR"
    TYPE_EQUATION    = "CMD_TYPE_EQUATION"
    TYPE_INEQUALITY  = "CMD_TYPE_INEQUALITY"
    TYPE_EXPRESSION  = "CMD_TYPE_EXPRESSION"

    # Square-root action — inserts "sqrt(" into the expression
    SQRT = "CMD_SQRT"

    # For matrix keypad only (hardware double SHIFT)
    SHIFT_A   = "CMD_SHIFT_A"
    SHIFT_B   = "CMD_SHIFT_B"
    SHIFT     = "SHIFT"


class KeypadBase:
    """
    Abstract interface for any keypad type.

    Concrete implementations:
      - keypad_matrix.py  → 4x4 matrix keypad via GPIO (machine.Pin)
      - keypad_ble_hid.py → BLE HID central macropad (ubluetooth)

    Contract:
      update() is called on every iteration of the main loop and returns a single
      value: a character ('0'-'9', 'x', '+', ...), a KeypadAction.*, or None if
      there is nothing new.
    """

    def update(self):
        """
        Reads the keypad state and returns the next event.

        Returns:
            str | None — character, KeypadAction.*, or None
        """
        raise NotImplementedError("update() must be implemented by the subclass")

    def reset_shift(self):
        """
        Resets the software shift/layer state (if applicable).
        Called by main.py after every submission to the RPi.
        Implementations without software shift can ignore it.
        """
        pass