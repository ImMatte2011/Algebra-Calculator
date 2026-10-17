"""Expression editing, mode/action menus, packet preparation, and local history."""

from drivers.keypad_base import KeypadAction
from core.history import History


class InputHandler:
    """Manages expression state and prepares packets for the Android bridge."""

    MAX_EXPRESSION_LENGTH = 200

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
    MODE_MENU = {
        "1": "algebra",
        "2": "system",
        "3": "number",
        "4": "matrix",
        "5": "function",
    }
    MODE_LABELS = {
        "algebra": "alg",
        "system": "sys",
        "number": "num",
        "matrix": "mat",
        "function": "fn",
    }
    MODE_ACTION_MENU = {
        "system": {
            "1": ("lin_system", None, "lin"),
            "2": ("ineq_system", None, "ineq"),
        },
        "number": {
            "1": ("number", "primes", "primes"),
            "2": ("number", "gcd", "gcd"),
            "3": ("number", "lcm", "lcm"),
        },
        "matrix": {
            "1": ("matrix", "det", "det"),
            "2": ("matrix", "inv", "inv"),
            "3": ("matrix", "trans", "trans"),
        },
        "function": {
            "1": ("function", "define", "def"),
            "2": ("function", "list", "list"),
            "3": ("function", "delete", "del"),
        },
    }
    _ACTIONLESS_TYPES = ("equation", "inequality", "lin_system", "ineq_system")
    _DIRECT_KEYS = (
        KeypadAction.ACTION_SIMPLIFY,
        KeypadAction.ACTION_EXPAND,
        KeypadAction.ACTION_FACTOR,
        KeypadAction.TYPE_EQUATION,
        KeypadAction.TYPE_INEQUALITY,
        KeypadAction.TYPE_EXPRESSION,
    )
    FUNC_NAMES = ("f", "g", "h")

    def __init__(self, history_size=10):
        self.expr = ""
        self.cursor_pos = 0
        self.last_local_result = None
        self.waiting_menu = False
        self.menu_stage = "type"
        self.menu_choice = None
        self.expression_action = None
        self.mode = "algebra"
        self.history = History(history_size)
        self._hist_idx = None
        self._draft = ""
        self._last_packet = None
        self._after_func = False

    def process_key(self, key):
        if key is None:
            return None

        cycling = self._after_func
        self._after_func = key == KeypadAction.FUNC

        if self.waiting_menu and self.menu_stage == "mode":
            return self._handle_menu_key(key)

        if self.mode != "algebra" and key in self._DIRECT_KEYS:
            key = KeypadAction.ENTER

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
            return self._open_menu("expression_action")
        if key == KeypadAction.SQRT:
            if not self._insert_char("sqrt("):
                return {"input_error": "expression_too_long"}
            return None
        if key == KeypadAction.FUNC:
            if not self._insert_func_name(cycling):
                return {"input_error": "expression_too_long"}
            return None
        if self.waiting_menu:
            return self._handle_menu_key(key)
        return self._handle_edit_key(key)

    def _direct_packet(self, request_type, action=None):
        if not self.expr.strip():
            return {"menu_error": "empty_expression"}
        return self.prepare_packet(request_type, act=action)

    def _handle_edit_key(self, key):
        if key == KeypadAction.BACKSPACE:
            self._delete_previous()
        elif key == KeypadAction.DELETE:
            self._delete_next()
        elif key == KeypadAction.CLEAR:
            if not self.expr and self._hist_idx is None:
                return self.open_mode_menu()
            self.reset()
        elif key == KeypadAction.ENTER:
            return self._open_menu("type" if self.mode == "algebra" else "mode_action")
        elif key == KeypadAction.LEFT:
            self._move_cursor(-1)
        elif key == KeypadAction.RIGHT:
            self._move_cursor(1)
        elif key == KeypadAction.UP:
            self._history_step(1)
        elif key == KeypadAction.DOWN:
            self._history_step(-1)
        elif key in (KeypadAction.SHIFT, KeypadAction.SHIFT_A, KeypadAction.SHIFT_B):
            pass
        elif isinstance(key, str) and not self._insert_char(key):
            return {"input_error": "expression_too_long"}
        return None

    def open_mode_menu(self):
        self._hist_idx = None
        return self._open_menu("mode")

    def _open_menu(self, stage):
        self.waiting_menu = True
        self.menu_stage = stage
        self.menu_choice = None
        return {"menu_open": True, "prompt": self.get_menu_prompt()}

    def _handle_menu_key(self, key):
        if key == KeypadAction.CLEAR:
            self.cancel_menu()
            return {"menu_cancelled": True}
        if isinstance(key, str) and key in [choice for choice, _ in self._menu_items()]:
            self.menu_choice = key
            return {"menu_choice": key}
        if key != KeypadAction.ENTER:
            return None
        if self.menu_choice is None:
            return {"menu_error": "select_type"}

        if self.menu_stage == "mode":
            self.mode = self.MODE_MENU[self.menu_choice]
            self._reset_menu()
            return {"mode_changed": self.mode}
        if self.menu_stage == "mode_action":
            request_type, action, _ = self.MODE_ACTION_MENU[self.mode][self.menu_choice]
            packet = self.prepare_packet(request_type, act=action)
            self._reset_menu()
            return packet
        if self.menu_stage == "type":
            request_type = self.menu_choice_to_type(self.menu_choice)
            if request_type == "expression":
                return self._open_menu("expression_action")
            packet = self.prepare_packet(request_type)
            self._reset_menu()
            return packet
        if self.menu_stage == "expression_action":
            action = self.EXPR_ACTION_MENU[self.menu_choice]
            packet = self.prepare_packet("expression", act=action)
            self._reset_menu()
            return packet
        return None

    def _history_step(self, direction):
        count = len(self.history)
        if count == 0:
            return
        if self._hist_idx is None:
            if direction < 0:
                return
            self._draft = self.expr
            self._hist_idx = 0
        else:
            new_index = self._hist_idx + direction
            if new_index < 0:
                self._hist_idx = None
                self.expr = self._draft
                self.cursor_pos = len(self.expr)
                return
            if new_index >= count:
                return
            self._hist_idx = new_index
        self.expr = self.history.get(self._hist_idx)[0]
        self.cursor_pos = len(self.expr)

    def history_status(self):
        if self._hist_idx is None:
            return ""
        return "H{}/{} {}".format(
            self._hist_idx + 1,
            len(self.history),
            self.history.get(self._hist_idx)[3],
        )

    def _insert_char(self, char):
        if len(self.expr) + len(char) > self.MAX_EXPRESSION_LENGTH:
            return False
        self._hist_idx = None
        self.expr = self.expr[:self.cursor_pos] + char + self.expr[self.cursor_pos:]
        self.cursor_pos = min(self.cursor_pos + len(char), len(self.expr))
        return True

    def _insert_func_name(self, cycling):
        before = self.expr[:self.cursor_pos]
        if (cycling and len(before) >= 2 and before[-1] == "("
                and before[-2] in self.FUNC_NAMES):
            next_name = self.FUNC_NAMES[
                (self.FUNC_NAMES.index(before[-2]) + 1) % len(self.FUNC_NAMES)
            ]
            self.expr = before[:-2] + next_name + "(" + self.expr[self.cursor_pos:]
            self._hist_idx = None
            return True
        return self._insert_char(self.FUNC_NAMES[0] + "(")

    def _delete_next(self):
        if self.cursor_pos < len(self.expr):
            self._hist_idx = None
            self.expr = self.expr[:self.cursor_pos] + self.expr[self.cursor_pos + 1:]

    def _delete_previous(self):
        if self.cursor_pos > 0:
            self._hist_idx = None
            self.expr = self.expr[:self.cursor_pos - 1] + self.expr[self.cursor_pos:]
            self.cursor_pos -= 1

    def _move_cursor(self, delta):
        self.cursor_pos = max(0, min(self.cursor_pos + delta, len(self.expr)))

    def prepare_packet(self, request_type, act=None, val=None):
        if request_type is None:
            raise ValueError("request_type must be provided")
        if request_type in self._ACTIONLESS_TYPES:
            act = None
            val = None
        expression = "list" if request_type == "function" and act == "list" else self.expr
        packet = (expression, request_type, act, val)
        self._last_packet = packet
        return packet

    def _menu_items(self):
        if self.menu_stage == "mode":
            return [
                (key, self.MODE_LABELS[mode])
                for key, mode in sorted(self.MODE_MENU.items())
            ]
        if self.menu_stage == "mode_action":
            return [
                (key, value[2])
                for key, value in sorted(self.MODE_ACTION_MENU[self.mode].items())
            ]
        if self.menu_stage == "expression_action":
            return [
                (key, action[:4])
                for key, action in sorted(self.EXPR_ACTION_MENU.items())
            ]
        short = {"expression": "expr", "equation": "eq", "inequality": "ineq"}
        return [
            (key, short.get(value, value[:4]))
            for key, value in sorted(self.REQUEST_TYPE_MENU.items())
        ]

    def menu_size(self):
        return len(self._menu_items())

    def get_menu_prompt(self):
        labels = ["{}={}".format(key, label) for key, label in self._menu_items()]
        return " ".join(labels[:2]), " ".join(labels[2:])

    @classmethod
    def menu_choice_to_type(cls, choice):
        return cls.REQUEST_TYPE_MENU.get(str(choice))

    def cancel_menu(self):
        self._reset_menu()

    def _reset_menu(self):
        self.waiting_menu = False
        self.menu_stage = "type"
        self.menu_choice = None
        self.expression_action = None

    def store_local_result(self, result):
        self.last_local_result = result
        if self._last_packet is not None:
            expression, request_type, action, _ = self._last_packet
            if not (request_type == "function" and action == "list"):
                self.history.add(expression, request_type, action, result)
            self._last_packet = None
        self._hist_idx = None

    def reset(self):
        self.expr = ""
        self.cursor_pos = 0
        self._hist_idx = None
        self._draft = ""
        self._reset_menu()

    def get_state(self):
        return {
            "expr": self.expr,
            "cursor_pos": self.cursor_pos,
            "waiting_menu": self.waiting_menu,
            "menu_choice": self.menu_choice,
            "last_local_result": self.last_local_result,
            "mode": self.mode,
        }
