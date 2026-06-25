"""
keypad_ble_hid.py — Driver BLE HID central per MINI-KEYBOARD.

Implementa KeypadBase connettendosi al macropad come BLE central (client),
sottoscrivendo le notifiche HID Report e convertendo ogni keycode ricevuto
in un KeypadAction o in un carattere testuale.

Usato quando CONFIG["KEYPAD_TYPE"] == "ble_hid".
La logica di switch BLE (central ↔ peripheral) è in ble_mode_manager.py,
non qui: questo modulo conosce solo il tastierino, non il telefono.
"""

import ubluetooth
import time
from drivers.keypad_base import KeypadAction, KeypadBase
from utils import logger

# MAC del macropad (confermato da nRF Connect e hid_mapper.py)
_TARGET_MAC = "E0:0F:7A:C3:C9:DF"

# UUID standard HID
_UUID_HID_SERVICE = ubluetooth.UUID(0x1812)
_UUID_HID_REPORT  = ubluetooth.UUID(0x2A4D)
_UUID_BOOT_MOUSE  = ubluetooth.UUID(0x2A33)
_UUID_CCCD        = ubluetooth.UUID(0x2902)
_NOTIFY_ENABLE    = b'\x01\x00'

# ---------------------------------------------------------------------------
# Lookup table HID keycode → carattere
# (confermata da hid_mapper.py — tutti handle=43, standard HID)
# ---------------------------------------------------------------------------
_SHIFTED = 0x22   # LSHIFT=0x02 | RSHIFT=0x20

_HID_CHAR = {
    0x04: ('a','A'), 0x05: ('b','B'), 0x06: ('c','C'), 0x07: ('d','D'),
    0x08: ('e','E'), 0x09: ('f','F'), 0x0A: ('g','G'), 0x0B: ('h','H'),
    0x0C: ('i','I'), 0x0D: ('j','J'), 0x0E: ('k','K'), 0x0F: ('l','L'),
    0x10: ('m','M'), 0x11: ('n','N'), 0x12: ('o','O'), 0x13: ('p','P'),
    0x14: ('q','Q'), 0x15: ('r','R'), 0x16: ('s','S'), 0x17: ('t','T'),
    0x18: ('u','U'), 0x19: ('v','V'), 0x1A: ('w','W'), 0x1B: ('x','X'),
    0x1C: ('y','Y'), 0x1D: ('z','Z'),
    0x1E: ('1','!'), 0x1F: ('2','@'), 0x20: ('3','#'), 0x21: ('4','$'),
    0x22: ('5','%'), 0x23: ('6','^'), 0x24: ('7','&'), 0x25: ('8','*'),
    0x26: ('9','('), 0x27: ('0',')'),
    0x2D: ('-','_'), 0x2E: ('=','+'),
    0x2F: ('[','{'), 0x30: (']','}'), 0x31: ('\\','|'),
    0x33: (';',':'), 0x34: ("'",'"'), 0x35: ('`','~'),
    0x36: (',','<'), 0x37: ('.','>')  , 0x38: ('/','?'),
}

# Keycodes → KeypadAction (non dipendono dal modifier)
_HID_ACTION = {
    0x28: KeypadAction.ENTER,
    0x29: KeypadAction.CLEAR,       # ESC → CLEAR
    0x2A: KeypadAction.BACKSPACE,
    0x4C: KeypadAction.DELETE,
    0x4F: KeypadAction.RIGHT,
    0x50: KeypadAction.LEFT,
    0x51: KeypadAction.DOWN,
    0x52: KeypadAction.UP,
}

# F13-F18 → azioni matematiche (Layer 3 del macropad)
_HID_FN = {
    0x68: KeypadAction.ACTION_SIMPLIFY,
    0x69: KeypadAction.ACTION_EXPAND,
    0x6A: KeypadAction.ACTION_FACTOR,
    0x6B: KeypadAction.TYPE_EQUATION,
    0x6C: KeypadAction.TYPE_INEQUALITY,
    0x6D: KeypadAction.TYPE_EXPRESSION,
}

# Moltiplicazione: il macropad manda '*' (0x25 + SHIFT = '*')
# ma nel layer 1 l'abbiamo mappato direttamente come 0x55 (keypad *)
# o come Shift+8 — dopo i test aggiornare qui se necessario
# Per ora: Shift+8 (0x25) = '*'


def _decode(keycode, modifier):
    """Converte (keycode, modifier) in KeypadAction o carattere. None = ignora."""
    if keycode == 0:
        return None

    # Azioni speciali (F13-F18)
    if keycode in _HID_FN:
        return _HID_FN[keycode]

    # Comandi di controllo
    if keycode in _HID_ACTION:
        return _HID_ACTION[keycode]

    # Caratteri
    if keycode in _HID_CHAR:
        shifted = bool(modifier & _SHIFTED)
        return _HID_CHAR[keycode][1 if shifted else 0]

    return None   # keycode sconosciuto, ignora


# ---------------------------------------------------------------------------
# Driver BLE HID
# ---------------------------------------------------------------------------
class KeypadBleHid(KeypadBase):
    """
    Tastierino BLE HID come BLE central.

    Connessione automatica, riconnessione su disconnessione inattesa,
    coda thread-safe (IRQ → coda → poll nel loop principale).
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
        """
        Args:
            ble_instance: istanza ubluetooth.BLE già attiva, oppure None
                          per crearne una interna. Passare l'istanza esterna
                          quando si condivide BLE con ble_mode_manager.
        """
        if ble_instance:
            self._ble = ble_instance
        else:
            self._ble = ubluetooth.BLE()
            self._ble.active(True)

        self._ble.irq(self._irq)

        self._conn           = None
        self._phase          = "idle"
        self._event_queue    = []        # [(keycode, modifier), ...]
        self._cccd_queue     = []
        self._all_services   = []
        self._report_handles = []
        self._hid_service    = None
        self._current_char_idx = 0
        self._last_disconnect_ms = 0
        self.on_state_change = None      # callback(state: str) per aggiornare il display

        self._connect()

    # -----------------------------------------------------------------------
    # Connessione
    # -----------------------------------------------------------------------
    def _connect(self):
        parts = _TARGET_MAC.split(":")
        addr  = bytes(int(x, 16) for x in parts)
        logger.info("KeypadBleHid: connessione a %s", _TARGET_MAC)
        self._phase = "connecting"
        self._ble.gap_connect(0, addr)
        self._notify_state("connecting")

    def _notify_state(self, state):
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # IRQ
    # -----------------------------------------------------------------------
    def _irq(self, event, data):
        if event == self._IRQ_PERIPHERAL_CONNECT:
            conn, _, _ = data
            self._conn  = conn
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
            if u == _UUID_HID_REPORT or u == _UUID_BOOT_MOUSE:
                # Teniamo solo le caratteristiche con NOTIFY (bit 4 = 0x10)
                if props & 0x10:
                    self._report_handles.append((def_h, val_h))

        elif event == self._IRQ_GATTC_CHARACTERISTIC_DONE:
            self._phase = "discover_desc"
            self._current_char_idx = 0
            self._discover_next_desc()

        elif event == self._IRQ_GATTC_DESCRIPTOR_RESULT:
            _, dsc_h, uuid = data
            if ubluetooth.UUID(uuid) == _UUID_CCCD:
                # Associa questo CCCD all'ultimo value_handle in discovery
                if self._current_char_idx <= len(self._report_handles):
                    vh = self._report_handles[self._current_char_idx - 1][1]
                    self._cccd_queue.append((vh, dsc_h))

        elif event == self._IRQ_GATTC_DESCRIPTOR_DONE:
            self._current_char_idx += 1
            self._discover_next_desc()

        elif event == self._IRQ_GATTC_WRITE_DONE:
            self._enable_next_cccd()

        elif event == self._IRQ_GATTC_NOTIFY:
            _, value_handle, notify_data = data
            raw = bytes(notify_data)
            if len(raw) >= 3 and raw[1] == 0x00:
                # Report tastiera standard: [modifier, 0x00, key1..key6]
                modifier = raw[0]
                for kc in raw[2:]:
                    if kc != 0:
                        self._event_queue.append((kc, modifier))
            elif len(raw) >= 2:
                # Consumer / altro report: prova come keycode diretto
                modifier = 0
                kc = raw[1]
                if kc != 0:
                    self._event_queue.append((kc, modifier))

    def _discover_next_desc(self):
        if self._current_char_idx >= len(self._report_handles):
            logger.info("KeypadBleHid: abilito %d notifiche", len(self._cccd_queue))
            self._enable_next_cccd()
            return
        def_h, val_h = self._report_handles[self._current_char_idx]
        if self._current_char_idx + 1 < len(self._report_handles):
            end = self._report_handles[self._current_char_idx + 1][0] - 1
        else:
            end = self._hid_service[1]
        self._ble.gattc_discover_descriptors(self._conn, def_h, end)

    def _enable_next_cccd(self):
        if self._cccd_queue:
            vh, dsc_h = self._cccd_queue.pop(0)
            self._ble.gattc_write(self._conn, dsc_h, _NOTIFY_ENABLE, 1)
        else:
            self._phase = "ready"
            logger.info("KeypadBleHid: pronto")
            self._notify_state("ready")

    # -----------------------------------------------------------------------
    # KeypadBase interface
    # -----------------------------------------------------------------------
    def update(self):
        """
        Chiamato ogni iterazione del loop. Gestisce la riconnessione e
        restituisce il prossimo evento dalla coda, oppure None.
        """
        # Riconnessione automatica dopo disconnessione
        if self._phase == "disconnected":
            elapsed = time.ticks_diff(time.ticks_ms(), self._last_disconnect_ms)
            if elapsed >= self.RECONNECT_DELAY_MS:
                self._connect()
            return None

        if self._phase != "ready":
            return None

        if not self._event_queue:
            return None

        keycode, modifier = self._event_queue.pop(0)
        return _decode(keycode, modifier)

    def is_ready(self):
        return self._phase == "ready"

    def is_connected(self):
        return self._conn is not None