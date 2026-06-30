"""
keypad_ble_hid.py — Driver BLE HID central per MINI-KEYBOARD.

Implementa KeypadBase connettendosi al macropad come BLE central (client).
Mappa ricavata da hid_mapper.py sul dispositivo reale (E0:0F:7A:C3:C9:DF).

Usato quando CONFIG["KEYPAD_TYPE"] == "ble_hid".
"""

import ubluetooth
import time
from drivers.keypad_base import KeypadAction, KeypadBase
from config import CONFIG
from utils import logger

_MAC = CONFIG["BLE_KP_MAC"]

_UUID_HID_SERVICE = ubluetooth.UUID(0x1812)
_UUID_HID_REPORT  = ubluetooth.UUID(0x2A4D)
_UUID_BOOT_MOUSE  = ubluetooth.UUID(0x2A33)
_UUID_CCCD        = ubluetooth.UUID(0x2902)
_NOTIFY_ENABLE    = b'\x01\x00'

_MOD_SHIFT = 0x22   # LSHIFT | RSHIFT

# ---------------------------------------------------------------------------
# Caratteri (senza_shift, con_shift) — solo i keycode realmente usati dal
# macropad, confermati da hid_mapper.py. Nessuna tabella alfabetica
# completa: non serve, il macropad non manda lettere libere.
# ---------------------------------------------------------------------------
_HID_CHAR = {
    # Numpad (Layer 1)
    0x59: ('1', '1'), 0x5A: ('2', '2'), 0x5B: ('3', '3'),
    0x5C: ('4', '4'), 0x5D: ('5', '5'), 0x5E: ('6', '6'),
    0x5F: ('7', '7'), 0x60: ('8', '8'), 0x61: ('9', '9'),
    0x62: ('0', '0'),
    0x57: ('+', '+'), 0x56: ('-', '-'), 0x55: ('*', '*'), 0x54: ('/', '/'),
    0x1B: ('x', 'x'),   # incognita

    # Layer 2 — simboli ed equazioni
    0x23: ('6', '^'),   # SHIFT+6 → ^ (esponente)
    0x26: ('9', '('),   # SHIFT+9 → (
    0x27: ('0', ')'),   # SHIFT+0 → )
    0x36: (',', '<'),   # SHIFT+, → <
    0x37: ('.', '>'),   # SHIFT+. → >
    0x2E: ('=', '='),   # =
    0x1E: ('1', '!'),   # SHIFT+1 → !
}

# Azioni di controllo — indipendenti dal modifier
_HID_ACTION = {
    0x28: KeypadAction.ENTER,    # numpad ENTER
    0x29: KeypadAction.CLEAR,    # ESC (anche click knob 3)
    0x2A: KeypadAction.BACKSPACE,
    0x4C: KeypadAction.DELETE,
    0x4F: KeypadAction.RIGHT,
    0x50: KeypadAction.LEFT,
    0x51: KeypadAction.DOWN,
    0x52: KeypadAction.UP,
}

# F-key azioni matematiche dirette (Layer 3).
# F1-F6 assegnate alle 6 azioni; F7-F16 libere per espansioni future.
# F17 (0x6C) riservata a SQRT (sostituisce la vecchia macro testuale "sqrt").
_HID_FN = {
    0x3A: KeypadAction.ACTION_SIMPLIFY,   # F1
    0x3B: KeypadAction.ACTION_EXPAND,     # F2
    0x3C: KeypadAction.ACTION_FACTOR,     # F3
    0x3D: KeypadAction.TYPE_EQUATION,     # F4
    0x3E: KeypadAction.TYPE_INEQUALITY,   # F5
    0x3F: KeypadAction.TYPE_EXPRESSION,   # F6
    # F7-F16 (0x40-0x45, 0x68-0x6B): libere, aggiungere qui se servono
    0x6C: KeypadAction.SQRT,              # F17 — radice (remap nel tool)
}


def _decode(keycode, modifier):
    """Converte (keycode, modifier) in KeypadAction o carattere. None = ignora."""
    if keycode == 0:
        return None
    if keycode in _HID_FN:
        return _HID_FN[keycode]
    if keycode in _HID_ACTION:
        return _HID_ACTION[keycode]
    if keycode in _HID_CHAR:
        shifted = bool(modifier & _MOD_SHIFT)
        return _HID_CHAR[keycode][1 if shifted else 0]
    logger.debug("HID keycode sconosciuto: 0x%02X mod=0x%02X", keycode, modifier)
    return None


# ---------------------------------------------------------------------------
# Driver BLE HID Central
# ---------------------------------------------------------------------------
class KeypadBleHid(KeypadBase):
    """Tastierino BLE HID come BLE central. Riconnessione automatica."""

    _IRQ_PERIPHERAL_CONNECT           = 7
    _IRQ_PERIPHERAL_DISCONNECT        = 8
    _IRQ_GATTC_SERVICE_RESULT         = 9
    _IRQ_GATTC_SERVICE_DONE           = 10
    _IRQ_GATTC_CHARACTERISTIC_RESULT  = 11
    _IRQ_GATTC_CHARACTERISTIC_DONE    = 12
    _IRQ_GATTC_DESCRIPTOR_RESULT      = 13
    _IRQ_GATTC_DESCRIPTOR_DONE        = 14
    _IRQ_GATTC_WRITE_DONE             = 17
    _IRQ_GATTC_NOTIFY                 = 18

    RECONNECT_DELAY_MS = 3000

    def __init__(self, ble_instance=None):
        if ble_instance:
            self._ble = ble_instance
        else:
            self._ble = ubluetooth.BLE()
            self._ble.active(True)
        self._ble.irq(self._irq)

        self._conn              = None
        self._phase             = "idle"
        self._event_queue       = []
        self._cccd_queue        = []
        self._all_services      = []
        self._report_handles    = []
        self._hid_service       = None
        self._current_char_idx  = 0
        self._last_disconnect_ms = 0
        self.on_state_change    = None

        self._connect()

    def _connect(self):
        parts = _MAC.split(":")
        addr  = bytes(int(x, 16) for x in parts)
        logger.info("KeypadBleHid: connessione a %s", _MAC)
        self._phase = "connecting"
        self._ble.gap_connect(0, addr)
        self._notify_state("connecting")

    def _notify_state(self, state):
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception:
                pass

    def _irq(self, event, data):
        if event == self._IRQ_PERIPHERAL_CONNECT:
            conn, _, _ = data
            self._conn = conn
            self._phase = "discover_services"
            self._all_services   = []
            self._report_handles = []
            self._cccd_queue     = []
            self._ble.gattc_discover_services(conn)

        elif event == self._IRQ_PERIPHERAL_DISCONNECT:
            self._conn  = None
            self._phase = "disconnected"
            self._last_disconnect_ms = time.ticks_ms()
            logger.info("KeypadBleHid: disconnesso")
            self._notify_state("disconnected")

        elif event == self._IRQ_GATTC_SERVICE_RESULT:
            _, s, e, uuid = data
            self._all_services.append((s, e, ubluetooth.UUID(uuid)))

        elif event == self._IRQ_GATTC_SERVICE_DONE:
            hid = [(s, e) for s, e, u in self._all_services if u == _UUID_HID_SERVICE]
            if hid:
                self._hid_service = hid[0]
                self._phase = "discover_chars"
                self._ble.gattc_discover_characteristics(self._conn, *hid[0])
            else:
                logger.warning("KeypadBleHid: servizio HID non trovato")

        elif event == self._IRQ_GATTC_CHARACTERISTIC_RESULT:
            _, def_h, val_h, props, uuid = data
            u = ubluetooth.UUID(uuid)
            if (u == _UUID_HID_REPORT or u == _UUID_BOOT_MOUSE) and (props & 0x10):
                self._report_handles.append((def_h, val_h))

        elif event == self._IRQ_GATTC_CHARACTERISTIC_DONE:
            self._phase = "discover_desc"
            self._current_char_idx = 0
            self._discover_next_desc()

        elif event == self._IRQ_GATTC_DESCRIPTOR_RESULT:
            _, dsc_h, uuid = data
            if ubluetooth.UUID(uuid) == _UUID_CCCD and self._current_char_idx > 0:
                vh = self._report_handles[self._current_char_idx - 1][1]
                self._cccd_queue.append((vh, dsc_h))

        elif event == self._IRQ_GATTC_DESCRIPTOR_DONE:
            self._current_char_idx += 1
            self._discover_next_desc()

        elif event == self._IRQ_GATTC_WRITE_DONE:
            self._enable_next_cccd()

        elif event == self._IRQ_GATTC_NOTIFY:
            _, value_handle, notify_data = data
            self._handle_notify(bytes(notify_data))

    def _discover_next_desc(self):
        if self._current_char_idx >= len(self._report_handles):
            logger.info("KeypadBleHid: abilito %d notifiche", len(self._cccd_queue))
            self._enable_next_cccd()
            return
        def_h, _ = self._report_handles[self._current_char_idx]
        if self._current_char_idx + 1 < len(self._report_handles):
            end = self._report_handles[self._current_char_idx + 1][0] - 1
        else:
            end = self._hid_service[1]
        self._ble.gattc_discover_descriptors(self._conn, def_h, end)

    def _enable_next_cccd(self):
        if self._cccd_queue:
            _, dsc_h = self._cccd_queue.pop(0)
            self._ble.gattc_write(self._conn, dsc_h, _NOTIFY_ENABLE, 1)
        else:
            self._phase = "ready"
            logger.info("KeypadBleHid: pronto")
            self._notify_state("ready")

    def _handle_notify(self, data):
        # Report tastiera standard: 8 byte, [modifier, 0x00, key1..key6]
        if len(data) >= 3 and data[1] == 0x00:
            modifier = data[0]
            for kc in data[2:]:
                if kc != 0:
                    self._event_queue.append((kc, modifier))
        # Altri report (boot mouse, knob proprietari): non utilizzati
        # per ora, i knob mandano keycode standard già gestiti sopra.

    # -----------------------------------------------------------------------
    # KeypadBase interface
    # -----------------------------------------------------------------------
    def update(self):
        if self._phase == "disconnected":
            elapsed = time.ticks_diff(time.ticks_ms(), self._last_disconnect_ms)
            if elapsed >= self.RECONNECT_DELAY_MS:
                self._connect()
            return None

        if self._phase != "ready" or not self._event_queue:
            return None

        keycode, modifier = self._event_queue.pop(0)
        return _decode(keycode, modifier)

    def is_ready(self):
        return self._phase == "ready"

    def is_connected(self):
        return self._conn is not None