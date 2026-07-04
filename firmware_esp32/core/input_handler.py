"""
input_handler.py — Manages the expression state and prepares packets.

Compatible with both keypad types:
  Matrix 4x4: the user presses ENTER → interactive menu (type → action)
  BLE Macropad: Layer 3 sends ACTION_SIMPLIFY / TYPE_EQUATION / etc.
                directly → a ready packet without a menu
"""

from drivers.keypad_base import KeypadAction


class InputHandler:
    """Manages the expression state and prepares the data packet."""

    # Interactive menu (used with the matrix keypad or with Layer 3 TYPE_EXPRESSION,
    # which still requires an action choice)
    REQUEST_TYPE_MENU = {
        "1": "expression",
        "2": "equation",
        "3": "inequality",
    }

    EXPR_ACTION_MENU = {
        "1": "simplify",
        "2": "expand",
        "3": "factor",
    }

    def __init__(self):
        self.expr        = ""
        self.cursor_pos  = 0
        self.last_local_result = None
        self.waiting_menu      = False
        self.menu_stage        = "type"    # "type" | "expression_action"
        self.menu_choice       = None
        self.expression_action = None

    # -----------------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------------
    def process_key(self, key):
        """
        Handles a KeypadAction or a character.
        Returns:
          None          → display state update only (expr changed)
          dict          → UI event (menu_open, menu_choice, menu_cancelled, etc.)
          tuple         → ready packet (expression, type, action, val)
        """
        if key is None:
            return None

        # ---------------------------------------------------------------
        # Layer 3 BLE macropad: direct actions without a menu
        # ---------------------------------------------------------------
        if key == KeypadAction.ACTION_SIMPLIFY:
            return self._direct_packet("expression", "simplify")

        if key == KeypadAction.ACTION_EXPAND:
            return self._direct_packet("expression", "expand")

        if key == KeypadAction.ACTION_FACTOR:
            return self._direct_packet("expression", "factor")

        if key == KeypadAction.TYPE_EQUATION:
            return self._direct_packet("equation")

        if key == KeypadAction.TYPE_INEQUALITY:
            return self._direct_packet("inequality")

        if key == KeypadAction.TYPE_EXPRESSION:
            # Expression without a specific action: open the action submenu only.
            self.waiting_menu = True
            self.menu_stage   = "expression_action"
            self.menu_choice  = None
            return {"menu_open": True, "prompt": self.get_menu_prompt()}

        # Square-root symbol handling (layer 2).
        if key == KeypadAction.SQRT:
            self._insert_char("sqrt(")
            return None

        # ---------------------------------------------------------------
        # Interactive menu (matrix keypad or TYPE_EXPRESSION from Layer 3)
        # ---------------------------------------------------------------
        if self.waiting_menu:
            return self._handle_menu_key(key)

        # ---------------------------------------------------------------
        # Normal editing
        # ---------------------------------------------------------------
        return self._handle_edit_key(key)

    # -----------------------------------------------------------------------
    # Direct packet (Layer 3 BLE macropad)
    # -----------------------------------------------------------------------
    def _direct_packet(self, request_type, action=None):
        """Prepares and returns the packet without opening a menu."""
        if not self.expr.strip():
            return {"menu_error": "empty_expression"}
        packet = self.prepare_packet(request_type, act=action)
        # Do not reset: the user might want to edit and resend
        return packet

    # -----------------------------------------------------------------------
    # Editing
    # -----------------------------------------------------------------------
    def _handle_edit_key(self, key):
        if key == KeypadAction.BACKSPACE:
            self._delete_previous()
        elif key == KeypadAction.DELETE:
            self._delete_next()
        elif key == KeypadAction.CLEAR:
            self.reset()
        elif key == KeypadAction.ENTER:
            # ENTER on the matrix keypad opens the full menu
            self.waiting_menu = True
            self.menu_stage   = "type"
            self.menu_choice  = None
            return {"menu_open": True, "prompt": self.get_menu_prompt()}
        elif key == KeypadAction.LEFT:
            self._move_cursor(-1)
        elif key == KeypadAction.RIGHT:
            self._move_cursor(1)
        elif key in (KeypadAction.UP, KeypadAction.DOWN,
                     KeypadAction.SHIFT, KeypadAction.SHIFT_A,
                     KeypadAction.SHIFT_B):
            pass   # handled elsewhere or ignored
        elif isinstance(key, str):
            self._insert_char(key)
        return None

    # -----------------------------------------------------------------------
    # Interactive menu
    # -----------------------------------------------------------------------
    def _handle_menu_key(self, key):
        if key == KeypadAction.CLEAR:
            self.cancel_menu()
            return {"menu_cancelled": True}

        # Selection by number
        if isinstance(key, str):
            if self.menu_stage == "type" and key in self.REQUEST_TYPE_MENU:
                self.menu_choice = key
                return {"menu_choice": self.menu_choice}
            if self.menu_stage == "expression_action" and key in self.EXPR_ACTION_MENU:
                self.menu_choice = key
                return {"menu_choice": self.menu_choice}

        # Confirm with ENTER
        if key == KeypadAction.ENTER:
            if self.menu_choice is None:
                return {"menu_error": "select_type"}

            if self.menu_stage == "type":
                request_type = self.menu_choice_to_type(self.menu_choice)
                if request_type == "expression":
                    self.menu_stage  = "expression_action"
                    self.menu_choice = None
                    return {"menu_open": True, "prompt": self.get_menu_prompt()}
                packet = self.prepare_packet(request_type)
                self._reset_menu()
                return packet

            if self.menu_stage == "expression_action":
                action = self.EXPR_ACTION_MENU[self.menu_choice]
                packet = self.prepare_packet("expression", act=action)
                self._reset_menu()
                return packet

        return None

    # -----------------------------------------------------------------------
    # Editing helpers
    # -----------------------------------------------------------------------
    def _insert_char(self, char):
        self.expr = self.expr[:self.cursor_pos] + char + self.expr[self.cursor_pos:]
        self.cursor_pos = min(self.cursor_pos + len(char), len(self.expr))

    def _delete_next(self):
        if self.cursor_pos < len(self.expr):
            self.expr = self.expr[:self.cursor_pos] + self.expr[self.cursor_pos + 1:]

    def _delete_previous(self):
        if self.cursor_pos > 0:
            self.expr = self.expr[:self.cursor_pos - 1] + self.expr[self.cursor_pos:]
            self.cursor_pos -= 1

    def _move_cursor(self, delta):
        self.cursor_pos = max(0, min(self.cursor_pos + delta, len(self.expr)))

    # -----------------------------------------------------------------------
    # Packet
    # -----------------------------------------------------------------------
    def prepare_packet(self, request_type, act=None, val=None):
        if request_type is None:
            raise ValueError("request_type must be provided")
        if request_type != "expression":
            act = None
            val = None
        return (self.expr, request_type, act, val)

    # -----------------------------------------------------------------------
    # Menu helpers
    # -----------------------------------------------------------------------
    def get_menu_prompt(self):
        if self.menu_stage == "expression_action":
            items = sorted(self.EXPR_ACTION_MENU.items())
            labels = [f"{k}={v[:4]}" for k, v in items]
            return labels[0] + " " + labels[1], labels[2]

        items = sorted(self.REQUEST_TYPE_MENU.items())
        short = {"expression": "expr", "equation": "eq", "inequality": "ineq"}
        labels = [f"{k}={short.get(v, v[:4])}" for k, v in items]
        return labels[0] + " " + labels[1], labels[2]

    @classmethod
    def menu_choice_to_type(cls, choice):
        return cls.REQUEST_TYPE_MENU.get(str(choice))

    def cancel_menu(self):
        self._reset_menu()

    def _reset_menu(self):
        self.waiting_menu      = False
        self.menu_stage        = "type"
        self.menu_choice       = None
        self.expression_action = None

    def store_local_result(self, result):
        self.last_local_result = result

    def reset(self):
        self.expr       = ""
        self.cursor_pos = 0
        self._reset_menu()

    def get_state(self):
        return {
            "expr":            self.expr,
            "cursor_pos":      self.cursor_pos,
            "waiting_menu":    self.waiting_menu,
            "menu_choice":     self.menu_choice,
            "last_local_result": self.last_local_result,
        }
