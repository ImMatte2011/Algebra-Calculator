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

# UUID standard HID
_UUID_HID_SERVICE = ubluetooth.UUID(0x1812)
_UUID_HID_REPORT  = ubluetooth.UUID(0x2A4D)
_UUID_BOOT_MOUSE  = ubluetooth.UUID(0x2A33)
_UUID_CCCD        = ubluetooth.UUID(0x2902)
_NOTIFY_ENABLE    = b'\x01\x00'

# Bitmask modifier
_MOD_CTRL  = 0x11   # LCTRL | RCTRL
_MOD_SHIFT = 0x22   # LSHIFT | RSHIFT
_MOD_GUI   = 0x88   # LGUI | RGUI

# ---------------------------------------------------------------------------
# Lookup table keycode → (senza_shift, con_shift)
# Aggiornata con i numpad keycodes confermati da hid_mapper.py
# ---------------------------------------------------------------------------
_HID_CHAR = {
    # Lettere
    0x04: ('a','A'), 0x05: ('b','B'), 0x06: ('c','C'), 0x07: ('d','D'),
    0x08: ('e','E'), 0x09: ('f','F'), 0x0A: ('g','G'), 0x0B: ('h','H'),
    0x0C: ('i','I'), 0x0D: ('j','J'), 0x0E: ('k','K'), 0x0F: ('l','L'),
    0x10: ('m','M'), 0x11: ('n','N'), 0x12: ('o','O'), 0x13: ('p','P'),
    0x14: ('q','Q'), 0x15: ('r','R'), 0x16: ('s','S'), 0x17: ('t','T'),
    0x18: ('u','U'), 0x19: ('v','V'), 0x1A: ('w','W'), 0x1B: ('x','X'),
    0x1C: ('y','Y'), 0x1D: ('z','Z'),
    # Simboli (confermati dallo scan: SHIFT+0x23='^', SHIFT+0x25='*', ecc.)
    0x1E: ('1','!'), 0x1F: ('2','@'), 0x20: ('3','#'), 0x21: ('4','$'),
    0x22: ('5','%'), 0x23: ('6','^'), 0x24: ('7','&'), 0x25: ('8','*'),
    0x26: ('9','('), 0x27: ('0',')'),
    0x2D: ('-','_'), 0x2E: ('=','+'),
    0x2F: ('[','{'), 0x30: (']','}'), 0x31: ('\\','|'),
    0x33: (';',':'), 0x34: ("'",'"'), 0x35: ('`','~'),
    0x36: (',','<'), 0x37: ('.','>')  , 0x38: ('/','?'),
    # Numpad (confermati da hid_mapper.py: 0x59-0x62, 0x54-0x58)
    0x54: ('/','/' ), 0x55: ('*','*'), 0x56: ('-','-'), 0x57: ('+','+'),
    0x59: ('1','1'), 0x5A: ('2','2'), 0x5B: ('3','3'),
    0x5C: ('4','4'), 0x5D: ('5','5'), 0x5E: ('6','6'),
    0x5F: ('7','7'), 0x60: ('8','8'), 0x61: ('9','9'),
    0x62: ('0','0'), 0x63: ('.','.' ),
}

# Keycodes → KeypadAction (indipendenti dal modifier, controllati prima di _HID_CHAR)
_HID_ACTION = {
    0x28: KeypadAction.ENTER,
    0x58: KeypadAction.ENTER,       # Numpad ENTER
    0x29: KeypadAction.CLEAR,       # ESC → CLEAR
    0x2A: KeypadAction.BACKSPACE,
    0x4C: KeypadAction.DELETE,
    0x4F: KeypadAction.RIGHT,
    0x50: KeypadAction.LEFT,
    0x51: KeypadAction.DOWN,
    0x52: KeypadAction.UP,
}

# F13-F24 → azioni matematiche (Layer 3 del macropad)
# 0x68=F13 … 0x73=F24
# Mappa: assegna F13-F18 alle 6 azioni, F19-F24 libere per espansioni future
_HID_FN = {
    0x68: KeypadAction.ACTION_SIMPLIFY,   # F13
    0x69: KeypadAction.ACTION_EXPAND,     # F14
    0x6A: KeypadAction.ACTION_FACTOR,     # F15 — confermato nello scan
    0x6B: KeypadAction.TYPE_EQUATION,     # F16
    0x6C: KeypadAction.TYPE_INEQUALITY,   # F17
    0x6D: KeypadAction.TYPE_EXPRESSION,   # F18 — confermato nello scan
    # F19-F24 (0x6E-0x73): liberi, aggiungere qui se servono
}

# Knob CW/CCW mappati a F-keys (da rimappare nel tool del macropad)
# Esempio suggerito:
#   Knob 1 CW  → F5  (0x3E) → RIGHT  (già in scan)
#   Knob 1 CCW → F6  (0x3F) → LEFT
#   Knob 2 CW  → F7  (0x40) → DOWN
#   Knob 2 CCW → F8  (0x41) → UP
# Per ora F5 (0x3E) confermato = knob CW:
_HID_KNOB = {
    0x3E: KeypadAction.RIGHT,   # F5 = Knob 1 CW  → cursore destra
    0x3F: KeypadAction.LEFT,    # F6 = Knob 1 CCW → cursore sinistra
    0x40: KeypadAction.DOWN,    # F7 = Knob 2 CW  → giù (menu / history)
    0x41: KeypadAction.UP,      # F8 = Knob 2 CCW → su
}


def _decode(keycode, modifier):
    """
    Converte (keycode, modifier) in KeypadAction o carattere.
    Restituisce None per eventi da ignorare.

    Ordine di priorità:
      1. CTRL+A → CLEAR (combo confermata dallo scan)
      2. GUI+key  → ignora (tasti Windows, non usati dalla calcolatrice)
      3. F-key funzioni matematiche (Layer 3)
      4. F-key knob CW/CCW
      5. Azioni di controllo (ENTER, BKSP, frecce...)
      6. Caratteri con/senza SHIFT
    """
    if keycode == 0:
        return None

    # 1. CTRL+A → CLEAR (select-all + backspace, confermato hid_mapper)
    if modifier & _MOD_CTRL and keycode == 0x04:
        return KeypadAction.CLEAR

    # 2. Qualsiasi combo con GUI (Windows key) → ignora
    #    (knob non ancora rimappati, o azioni PC non rilevanti per ESP32)
    if modifier & _MOD_GUI:
        return None

    # 3. F-key azioni matematiche (Layer 3)
    if keycode in _HID_FN:
        return _HID_FN[keycode]

    # 4. F-key knob
    if keycode in _HID_KNOB:
        return _HID_KNOB[keycode]

    # 5. Azioni di controllo
    if keycode in _HID_ACTION:
        return _HID_ACTION[keycode]

    # 6. Caratteri
    if keycode in _HID_CHAR:
        shifted = bool(modifier & _MOD_SHIFT)
        return _HID_CHAR[keycode][1 if shifted else 0]

    # Keycode sconosciuto — logga solo in debug per non spammare
    logger.debug("HID keycode sconosciuto: 0x%02X mod=0x%02X", keycode, modifier)
    return None


# ---------------------------------------------------------------------------
# Driver BLE HID Central
# ---------------------------------------------------------------------------
class KeypadBleHid(KeypadBase):
    """
    Tastierino BLE HID come BLE central.
    Riconnessione automatica, coda eventi thread-safe (IRQ → coda → poll).
    """

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
            self._all_services  = []
            self._report_handles = []
            self._cccd_queue    = []
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
            self._handle_notify(value_handle, bytes(notify_data))

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

    def _handle_notify(self, value_handle, data):
        n = len(data)
        if n == 0:
            return

        # Report tastiera standard (handle=43 confermato): 8 byte, data[1]==0x00
        if n >= 3 and data[1] == 0x00:
            modifier = data[0]
            for kc in data[2:]:
                if kc != 0:
                    self._event_queue.append((kc, modifier))
            return

        # Consumer report (handle=50): [report_id, usage_lo, usage_hi]
        # usage=0x0000 = key-up, ignora
        if n >= 3:
            usage = data[1] | (data[2] << 8)
            if usage != 0:
                self._handle_consumer(usage)
            return

        # Report a 2 byte: [report_id, usage]
        if n == 2 and data[1] != 0:
            self._handle_consumer(data[1])
            return

        # RAW handle=62 (formato proprietario knob):
        # byte 6 = 0x01 press / 0x00 release — al momento ignorato
        # da implementare quando la mappatura knob sarà definitiva

    def _handle_consumer(self, usage):
        """Mappa usage Consumer Control in KeypadAction."""
        _consumer = {
            0x00E9: KeypadAction.RIGHT,    # volume up  → knob CW
            0x00EA: KeypadAction.LEFT,     # volume down → knob CCW
            0x00E2: KeypadAction.CLEAR,    # mute       → click knob (CLEAR)
            0x00B5: KeypadAction.RIGHT,    # next track
            0x00B6: KeypadAction.LEFT,     # prev track
        }
        action = _consumer.get(usage)
        if action:
            self._event_queue.append((None, None, action))

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

        event = self._event_queue.pop(0)

        # Evento consumer già risolto: (None, None, action)
        if len(event) == 3:
            return event[2]

        keycode, modifier = event
        return _decode(keycode, modifier)

    def is_ready(self):
        return self._phase == "ready"

    def is_connected(self):
        return self._conn is not None