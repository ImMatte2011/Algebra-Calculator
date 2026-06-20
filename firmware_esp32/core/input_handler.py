from drivers.keypad_abstract import KeypadAction


class InputHandler:
    """Gestisce lo stato dell'espressione e prepara il pacchetto dati."""

    REQUEST_TYPE_MENU = {
        "1": "expression",
        "2": "equation",
        "3": "disequation",
    }

    EXPR_ACTION_MENU = {
        "1": "simplify",
        "2": "expand",
        "3": "factor",
    }

    def __init__(self):
        self.expr = ""
        self.cursor_pos = 0
        self.last_local_result = None
        self.waiting_menu = False
        self.menu_stage = "type"
        self.menu_choice = None
        self.expression_action = None

    def process_key(self, key):
        """Gestisce il keypress in base allo stato corrente."""
        if key is None:
            return None

        if self.waiting_menu:
            return self._handle_menu_key(key)

        return self._handle_edit_key(key)

    def _handle_edit_key(self, key):
        if key == KeypadAction.BACKSPACE:
            self._delete_previous()
            return None
        elif key == KeypadAction.DELETE:
            self._delete_next()
            return None
        elif key == KeypadAction.CLEAR:
            self.reset()
            return None
        elif key == KeypadAction.ENTER:
            self.waiting_menu = True
            self.menu_choice = None
            return {"menu_open": True, "prompt": self.get_menu_prompt()}
        elif key == KeypadAction.LEFT:
            self._move_cursor(-1)
            return None
        elif key == KeypadAction.RIGHT:
            self._move_cursor(1)
            return None
        elif key == KeypadAction.UP or key == KeypadAction.DOWN:
            return None
        elif key == KeypadAction.SHIFT:
            return None
        elif key == "CMD_SHIFT_A" or key == "CMD_SHIFT_B":
            # SHIFT modes are handled by the keypad driver; ignore token here
            return None
        elif isinstance(key, str):
            self._insert_char(key)
            return None

        return None

    def _handle_menu_key(self, key):
        if key == KeypadAction.CLEAR:
            self.cancel_menu()
            return {"menu_cancelled": True}

        if isinstance(key, str):
            if self.menu_stage == "type" and key in self.REQUEST_TYPE_MENU:
                self.menu_choice = key
                return {"menu_choice": self.menu_choice}
            if self.menu_stage == "expression_action" and key in self.EXPR_ACTION_MENU:
                self.menu_choice = key
                return {"menu_choice": self.menu_choice}

        if key == KeypadAction.ENTER:
            if self.menu_choice is None:
                return {"menu_error": "select_type"}

            if self.menu_stage == "type":
                request_type = self.menu_choice_to_type(self.menu_choice)
                if request_type == "expression":
                    self.menu_stage = "expression_action"
                    self.menu_choice = None
                    return {"menu_open": True, "prompt": self.get_menu_prompt()}

                packet = self.prepare_packet(request_type)
                self.waiting_menu = False
                self.menu_stage = "type"
                self.menu_choice = None
                return packet

            if self.menu_stage == "expression_action":
                action = self.EXPR_ACTION_MENU[self.menu_choice]
                self.expression_action = action
                packet = self.prepare_packet("expression", act=action)
                self.waiting_menu = False
                self.menu_stage = "type"
                self.menu_choice = None
                self.expression_action = None
                return packet

        return None

    def _insert_char(self, char):
        self.expr = self.expr[: self.cursor_pos] + char + self.expr[self.cursor_pos :]
        self.cursor_pos = min(self.cursor_pos + len(char), len(self.expr))

    def _delete_next(self):
        if self.cursor_pos < len(self.expr):
            self.expr = self.expr[: self.cursor_pos] + self.expr[self.cursor_pos + 1 :]

    def _delete_previous(self):
        if self.cursor_pos > 0:
            self.expr = self.expr[: self.cursor_pos - 1] + self.expr[self.cursor_pos :]
            self.cursor_pos -= 1

    def _move_cursor(self, delta):
        self.cursor_pos = max(0, min(self.cursor_pos + delta, len(self.expr)))

    def store_local_result(self, result):
        self.last_local_result = result

    @classmethod
    def menu_choice_to_type(cls, choice):
        return cls.REQUEST_TYPE_MENU.get(str(choice))

    @staticmethod
    def _short_label(label: str) -> str:
        return {
            "expression": "expr",
            "equation": "eqn",
            "disequation": "diseq",
        }.get(label, label[:4])

    def get_menu_prompt(self):
        if self.menu_stage == "expression_action":
            items = sorted(self.EXPR_ACTION_MENU.items(), key=lambda item: int(item[0]))
            top = []
            bottom = []

            for index, (key, action) in enumerate(items):
                label = f"{key}={action[:4]}"
                if index < 2:
                    top.append(label)
                else:
                    bottom.append(label)

            return " ".join(top), " ".join(bottom)

        items = sorted(self.REQUEST_TYPE_MENU.items(), key=lambda item: int(item[0]))
        top = []
        bottom = []

        for index, (key, value) in enumerate(items):
            label = f"{key}={self._short_label(value)}"
            if index < 2:
                top.append(label)
            else:
                bottom.append(label)

        return " ".join(top), " ".join(bottom)

    def prepare_packet(self, request_type, act=None, val=None):
        if request_type is None:
            raise ValueError("request_type deve essere fornito dall'interfaccia utente")

        if request_type != "equation":
            act = None
            val = None

        return (self.expr, request_type, act, val)

    def cancel_menu(self):
        self.waiting_menu = False
        self.menu_stage = "type"
        self.menu_choice = None
        self.expression_action = None

    def reset(self):
        self.expr = ""
        self.cursor_pos = 0
        self.waiting_menu = False
        self.menu_stage = "type"
        self.menu_choice = None
        self.expression_action = None

    def get_state(self):
        return {
            "expr": self.expr,
            "cursor_pos": self.cursor_pos,
            "waiting_menu": self.waiting_menu,
            "menu_choice": self.menu_choice,
            "last_local_result": self.last_local_result,
        }
