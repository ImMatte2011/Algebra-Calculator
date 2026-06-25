"""
keypad_base.py — Interfaccia astratta per il tastierino.

Definisce KeypadAction (i comandi logici riconosciuti dall'InputHandler)
e KeypadBase (la classe astratta che ogni implementazione hardware deve
estendere). Il codice in main.py e input_handler.py dipende SOLO da
questi due, mai dai driver concreti.
"""


class KeypadAction:
    """Comandi logici prodotti dal tastierino, indipendenti dall'hardware."""
    ENTER     = "ENTER"
    BACKSPACE = "BACKSPACE"
    DELETE    = "DELETE"
    CLEAR     = "CLEAR"
    LEFT      = "LEFT"
    RIGHT     = "RIGHT"
    UP        = "UP"
    DOWN      = "DOWN"

    # Layer-based actions (F13-F18 su macropad BLE, o tasti dedicati su matrix)
    ACTION_SIMPLIFY  = "CMD_SIMPLIFY"
    ACTION_EXPAND    = "CMD_EXPAND"
    ACTION_FACTOR    = "CMD_FACTOR"
    TYPE_EQUATION    = "CMD_TYPE_EQUATION"
    TYPE_INEQUALITY  = "CMD_TYPE_INEQUALITY"
    TYPE_EXPRESSION  = "CMD_TYPE_EXPRESSION"

    # Solo per keypad matriciale (doppio SHIFT hardware)
    SHIFT_A   = "CMD_SHIFT_A"
    SHIFT_B   = "CMD_SHIFT_B"
    SHIFT     = "SHIFT"


class KeypadBase:
    """
    Interfaccia astratta per qualsiasi tipo di tastierino.

    Le implementazioni concrete:
      - keypad_matrix.py  → tastierino matriciale 4x4 via GPIO (machine.Pin)
      - keypad_ble_hid.py → macropad BLE HID central (ubluetooth)

    Contratto:
      update() viene chiamato ad ogni iterazione del loop principale e
      restituisce un singolo valore: un carattere ('0'-'9', 'x', '+', ...),
      un KeypadAction.*, oppure None se non c'è nulla di nuovo.
    """

    def update(self):
        """
        Legge lo stato del tastierino e restituisce il prossimo evento.

        Returns:
            str | None — carattere, KeypadAction.*, oppure None
        """
        raise NotImplementedError("update() deve essere implementato dalla sottoclasse")

    def reset_shift(self):
        """
        Resetta lo stato di shift/layer software (se applicabile).
        Chiamato da main.py dopo ogni invio al RPi.
        Le implementazioni che non hanno shift software possono ignorarlo.
        """
        pass