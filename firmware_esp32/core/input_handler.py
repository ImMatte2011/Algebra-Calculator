"""
input_handler.py — Gestione stato dell'espressione e preparazione pacchetti.

Compatibile con entrambi i tipi di tastierino:
  Matrix 4x4:  l'utente preme ENTER → menu interattivo (type → action)
  Macropad BLE: Layer 3 invia ACTION_SIMPLIFY / TYPE_EQUATION / ecc.
                direttamente → pacchetto pronto senza menu
"""

from drivers.keypad_base import KeypadAction


class InputHandler:
    """Gestisce lo stato dell'espressione e prepara il pacchetto dati."""

    # Menu interattivo (usato con matrix keypad o con Layer 3 TYPE_EXPRESSION
    # che richiede ancora la scelta dell'azione)
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
    # Entry point principale
    # -----------------------------------------------------------------------
    def process_key(self, key):
        """
        Gestisce un KeypadAction o carattere.
        Restituisce:
          None          → solo aggiornamento stato display (expr modificata)
          dict          → evento UI (menu_open, menu_choice, menu_cancelled, ecc.)
          tuple         → pacchetto pronto (expression, type, action, val)
        """
        if key is None:
            return None

        # ---------------------------------------------------------------
        # Layer 3 macropad BLE: azioni dirette senza menu
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
            # Espressione senza azione specificata → apri solo il sotto-menu azione
            self.waiting_menu = True
            self.menu_stage   = "expression_action"
            self.menu_choice  = None
            return {"menu_open": True, "prompt": self.get_menu_prompt()}

        # Gestione simbolo di radice (layer 2) 
        if key == KeypadAction.SQRT:
            self._insert_char("sqrt(")
            return None

        # ---------------------------------------------------------------
        # Menu interattivo (matrix keypad o TYPE_EXPRESSION da Layer 3)
        # ---------------------------------------------------------------
        if self.waiting_menu:
            return self._handle_menu_key(key)

        # ---------------------------------------------------------------
        # Editing normale
        # ---------------------------------------------------------------
        return self._handle_edit_key(key)

    # -----------------------------------------------------------------------
    # Pacchetto diretto (Layer 3 BLE macropad)
    # -----------------------------------------------------------------------
    def _direct_packet(self, request_type, action=None):
        """Prepara e restituisce il pacchetto senza aprire menu."""
        if not self.expr.strip():
            return {"menu_error": "empty_expression"}
        packet = self.prepare_packet(request_type, act=action)
        # Non resettiamo: l'utente potrebbe voler correggere e reinviare
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
            # ENTER con matrix keypad apre il menu completo
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
            pass   # gestiti altrove o ignorati
        elif isinstance(key, str):
            self._insert_char(key)
        return None

    # -----------------------------------------------------------------------
    # Menu interattivo
    # -----------------------------------------------------------------------
    def _handle_menu_key(self, key):
        if key == KeypadAction.CLEAR:
            self.cancel_menu()
            return {"menu_cancelled": True}

        # Selezione con numero
        if isinstance(key, str):
            if self.menu_stage == "type" and key in self.REQUEST_TYPE_MENU:
                self.menu_choice = key
                return {"menu_choice": self.menu_choice}
            if self.menu_stage == "expression_action" and key in self.EXPR_ACTION_MENU:
                self.menu_choice = key
                return {"menu_choice": self.menu_choice}

        # Conferma con ENTER
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
    # Pacchetto
    # -----------------------------------------------------------------------
    def prepare_packet(self, request_type, act=None, val=None):
        if request_type is None:
            raise ValueError("request_type deve essere fornito")
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