"""
hid_mapper.py — Mappatura tasti tastierino BLE HID (MINI-KEYBOARD)
MAC: E0:0F:7A:C3:C9:DF

Carica sull'ESP32 come main.py, apri il terminale seriale (Thonny /
mpremote / rshell) e premi ogni tasto uno alla volta.

Output per ogni evento:
  [KEYBOARD] modifier=SHIFT  key=0x04  → 'A'
  [CONSUMER] keycode=0x00E9  → volume_up
  [MOUSE]    buttons=0x00  x=0  y=0  wheel=1    ← probabile knob CW

Alla fine Ctrl+C: salva hid_keymap_raw.json sulla flash ESP32.

Comandi utili:
  mpremote cp hid_mapper.py :main.py + mpremote run main.py
  oppure incolla nel REPL di Thonny (Run > Run current script)
"""

import ubluetooth
import time
import json

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
TARGET_MAC  = "E0:0F:7A:C3:C9:DF"   # MAC del MINI-KEYBOARD da nRF Connect
OUTPUT_FILE = "hid_keymap_raw.json"

# UUID standard
_UUID_HID_SERVICE   = ubluetooth.UUID(0x1812)
_UUID_HID_REPORT    = ubluetooth.UUID(0x2A4D)
_UUID_BOOT_MOUSE    = ubluetooth.UUID(0x2A33)
_UUID_REPORT_REF    = ubluetooth.UUID(0x2908)   # Report Reference descriptor
_UUID_CCCD          = ubluetooth.UUID(0x2902)   # Client Characteristic Config

# Report Reference — tipo (byte 1 del descriptor 0x2908)
_REPORT_TYPE = {0x01: "INPUT", 0x02: "OUTPUT", 0x03: "FEATURE"}

# ---------------------------------------------------------------------------
# Lookup table HID keycode (Usage Page 0x07 — Keyboard)
# ---------------------------------------------------------------------------
_HID_KEYMAP = {
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
    0x28: ('ENTER',   'ENTER'),
    0x29: ('ESC',     'ESC'),
    0x2A: ('BKSP',    'BKSP'),
    0x2B: ('TAB',     'TAB'),
    0x2C: ('SPACE',   'SPACE'),
    0x2D: ('-', '_'), 0x2E: ('=', '+'),
    0x2F: ('[', '{'), 0x30: (']', '}'), 0x31: ('\\','|'),
    0x33: (';', ':'), 0x34: ("'", '"'), 0x35: ('`', '~'),
    0x36: (',', '<'), 0x37: ('.', '>'), 0x38: ('/', '?'),
    0x39: ('CAPS',  'CAPS'),
    0x4F: ('RIGHT', 'RIGHT'), 0x50: ('LEFT',  'LEFT'),
    0x51: ('DOWN',  'DOWN'),  0x52: ('UP',    'UP'),
    0x4A: ('HOME',  'HOME'),  0x4D: ('END',   'END'),
    0x4B: ('PGUP',  'PGUP'),  0x4E: ('PGDN',  'PGDN'),
    0x4C: ('DEL',   'DEL'),
}

# Lookup table HID Consumer Control (Usage Page 0x0C) — codici comuni
_CONSUMER_MAP = {
    0x00E2: 'mute',
    0x00E9: 'volume_up',
    0x00EA: 'volume_down',
    0x00B5: 'next_track',
    0x00B6: 'prev_track',
    0x00CD: 'play_pause',
    0x00B7: 'stop',
    0x0070: 'brightness_up',
    0x006F: 'brightness_down',
    0x019E: 'lock',
    0x0221: 'search',
    0x0223: 'home_browser',
    0x018A: 'email',
    0x0192: 'calculator',
}

def _shifted(mod): return bool(mod & 0x22)   # LSHIFT=0x02, RSHIFT=0x20

def _modifier_str(mod):
    parts = []
    if mod & 0x22: parts.append("SHIFT")
    if mod & 0x11: parts.append("CTRL")
    if mod & 0x44: parts.append("ALT")
    if mod & 0x88: parts.append("GUI")
    return "+".join(parts) if parts else "none"

def _decode_key(keycode, mod):
    if keycode == 0: return None
    entry = _HID_KEYMAP.get(keycode)
    if entry: return entry[1] if _shifted(mod) else entry[0]
    return f"0x{keycode:02X}"


# ---------------------------------------------------------------------------
# Mapper principale
# ---------------------------------------------------------------------------
class HidMapper:
    _IRQ_PERIPHERAL_CONNECT           = 7
    _IRQ_PERIPHERAL_DISCONNECT        = 8
    _IRQ_GATTC_SERVICE_RESULT         = 9
    _IRQ_GATTC_SERVICE_DONE           = 10
    _IRQ_GATTC_CHARACTERISTIC_RESULT  = 11
    _IRQ_GATTC_CHARACTERISTIC_DONE    = 12
    _IRQ_GATTC_DESCRIPTOR_RESULT      = 13
    _IRQ_GATTC_DESCRIPTOR_DONE        = 14
    _IRQ_GATTC_READ_RESULT            = 15
    _IRQ_GATTC_WRITE_DONE             = 17
    _IRQ_GATTC_NOTIFY                 = 18

    def __init__(self):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)

        self._conn    = None
        self._phase   = "idle"
        self._raw_log = []

        # GATT discovery state
        self._hid_service   = None     # (start_handle, end_handle)
        self._all_services  = []

        # Report characteristics scoperte: value_handle → {"type": "INPUT/OUTPUT/FEATURE", "id": N}
        self._report_info   = {}

        # handle specifici
        self._boot_mouse_handle = None

        # Per discovery sequenziale: lista di (value_handle, def_handle) delle Report chars
        self._report_chars  = []       # [(def_handle, value_handle), ...]
        self._current_char_idx = 0

        # CCCD e Report Reference da abilitare/leggere
        # Struttura: list of dict {"cccd": handle_or_None, "ref": handle_or_None, "vh": value_handle}
        self._char_descriptors = []    # accumulato durante discover_descriptors
        self._current_desc_vh  = None  # value_handle corrente di cui sto scoprendo i desc

        # Coda di CCCD da abilitare
        self._cccd_queue   = []
        # Coda di Report Reference da leggere
        self._ref_queue    = []

        # Handle value_handle → label (costruita leggendo Report Reference)
        self._handle_label = {}

    # -----------------------------------------------------------------------
    # Avvio
    # -----------------------------------------------------------------------
    def start(self):
        parts = TARGET_MAC.split(":")
        addr  = bytes(int(x, 16) for x in parts)
        print(f"Connessione a {TARGET_MAC} ...")
        self._phase = "connecting"
        self.ble.gap_connect(0, addr)

    # -----------------------------------------------------------------------
    # IRQ handler
    # -----------------------------------------------------------------------
    def _irq(self, event, data):

        if event == self._IRQ_PERIPHERAL_CONNECT:
            conn, addr_type, addr = data
            self._conn  = conn
            self._phase = "discover_services"
            print("Connesso. Scoperta servizi...")
            self.ble.gattc_discover_services(conn)

        elif event == self._IRQ_PERIPHERAL_DISCONNECT:
            print("Disconnesso.")
            self._conn  = None
            self._phase = "idle"

        # --- SERVICE DISCOVERY ---
        elif event == self._IRQ_GATTC_SERVICE_RESULT:
            conn, s, e, uuid = data
            self._all_services.append((s, e, ubluetooth.UUID(uuid)))

        elif event == self._IRQ_GATTC_SERVICE_DONE:
            hid = [(s, e) for s, e, u in self._all_services if u == _UUID_HID_SERVICE]
            if not hid:
                print("ERRORE: nessun servizio HID 0x1812 trovato.")
                return
            self._hid_service = hid[0]
            s, e = self._hid_service
            print(f"Servizio HID trovato ({s}-{e}). Scoperta caratteristiche...")
            self._phase = "discover_chars"
            self.ble.gattc_discover_characteristics(self._conn, s, e)

        # --- CHARACTERISTIC DISCOVERY ---
        elif event == self._IRQ_GATTC_CHARACTERISTIC_RESULT:
            conn, def_h, val_h, props, uuid = data
            u = ubluetooth.UUID(uuid)
            if u == _UUID_HID_REPORT:
                self._report_chars.append((def_h, val_h))
            elif u == _UUID_BOOT_MOUSE:
                self._boot_mouse_handle = val_h
                print(f"  Boot Mouse Report trovato, handle={val_h}")

        elif event == self._IRQ_GATTC_CHARACTERISTIC_DONE:
            print(f"  {len(self._report_chars)} Report chars trovate"
                  + (f", Boot Mouse handle={self._boot_mouse_handle}" if self._boot_mouse_handle else ""))
            # Scopriamo i descriptor di ogni Report char sequenzialmente
            self._phase = "discover_descriptors"
            self._current_char_idx = 0
            self._discover_next_char_descriptors()

        # --- DESCRIPTOR DISCOVERY ---
        elif event == self._IRQ_GATTC_DESCRIPTOR_RESULT:
            conn, dsc_h, uuid = data
            u = ubluetooth.UUID(uuid)
            if u == _UUID_CCCD:
                self._char_descriptors.append(("cccd", dsc_h, self._current_desc_vh))
            elif u == _UUID_REPORT_REF:
                self._char_descriptors.append(("ref", dsc_h, self._current_desc_vh))

        elif event == self._IRQ_GATTC_DESCRIPTOR_DONE:
            self._current_char_idx += 1
            self._discover_next_char_descriptors()

        # --- READ (Report Reference) ---
        elif event == self._IRQ_GATTC_READ_RESULT:
            conn, value_handle, data_bytes = data
            b = bytes(data_bytes)
            if len(b) >= 2:
                report_id   = b[0]
                report_type = _REPORT_TYPE.get(b[1], f"0x{b[1]:02X}")
                vh = self._ref_read_pending_vh
                self._handle_label[vh] = f"{report_type}(id={report_id})"
                print(f"    handle={vh} → {report_type}, report_id={report_id}")
            self._read_next_report_ref()

        # --- WRITE (abilita CCCD) ---
        elif event == self._IRQ_GATTC_WRITE_DONE:
            self._enable_next_cccd()

        # --- NOTIFICA (tasto premuto!) ---
        elif event == self._IRQ_GATTC_NOTIFY:
            conn, value_handle, notify_data = data
            self._handle_notify(value_handle, bytes(notify_data))

    # -----------------------------------------------------------------------
    # Discovery descriptor sequenziale (una char alla volta)
    # -----------------------------------------------------------------------
    def _discover_next_char_descriptors(self):
        if self._current_char_idx >= len(self._report_chars):
            # Tutti i descriptor scoperti: aggiungi Boot Mouse se presente
            if self._boot_mouse_handle:
                # Per Boot Mouse cerco il CCCD nello stesso range di handle
                s, e = self._hid_service
                # aggiungo manualmente alla coda — nRF Connect ha confermato il CCCD
                self._char_descriptors.append(("boot_mouse", None, self._boot_mouse_handle))
            self._finish_discovery()
            return

        def_h, val_h = self._report_chars[self._current_char_idx]
        self._current_desc_vh = val_h
        # scopri descriptor nel range (def_handle, prossimo def_handle - 1)
        if self._current_char_idx + 1 < len(self._report_chars):
            end = self._report_chars[self._current_char_idx + 1][0] - 1
        else:
            end = self._hid_service[1]
        self.ble.gattc_discover_descriptors(self._conn, def_h, end)

    def _finish_discovery(self):
        # Separa CCCD e Report Reference
        self._cccd_queue = [(vh, dsc_h) for kind, dsc_h, vh in self._char_descriptors
                            if kind == "cccd" and dsc_h is not None]
        self._ref_queue  = [(vh, dsc_h) for kind, dsc_h, vh in self._char_descriptors
                            if kind == "ref"  and dsc_h is not None]

        # Boot Mouse CCCD: dobbiamo trovarlo — skip per ora se non abbiamo l'handle
        # (lo script stamperà comunque gli eventi se arrivano)

        print(f"\n  {len(self._cccd_queue)} CCCD, {len(self._ref_queue)} Report Reference")
        print("  Leggo Report Reference per identificare le caratteristiche...")
        self._ref_read_pending_vh = None
        self._read_next_report_ref()

    # -----------------------------------------------------------------------
    # Lettura sequenziale Report Reference → identifica ogni Report char
    # -----------------------------------------------------------------------
    def _read_next_report_ref(self):
        if self._ref_queue:
            vh, dsc_h = self._ref_queue.pop(0)
            self._ref_read_pending_vh = vh
            self.ble.gattc_read(self._conn, dsc_h)
        else:
            # Finito: abilita le notifiche
            print("  Abilito notifiche (CCCD)...")
            self._enable_next_cccd()

    # -----------------------------------------------------------------------
    # Abilitazione notifiche sequenziale
    # -----------------------------------------------------------------------
    def _enable_next_cccd(self):
        if self._cccd_queue:
            vh, dsc_h = self._cccd_queue.pop(0)
            label = self._handle_label.get(vh, f"handle={vh}")
            print(f"  Abilito notifica per {label} (cccd={dsc_h})")
            self.ble.gattc_write(self._conn, dsc_h, b'\x01\x00', 1)
        else:
            self._phase = "ready"
            print()
            print("=" * 55)
            print("PRONTO — premi i tasti del tastierino")
            print("Premi anche i knob (CW, CCW e click)")
            print("Ctrl+C per fermare e salvare il log")
            print("=" * 55)
            print()

    # -----------------------------------------------------------------------
    # Parsing degli eventi HID
    # -----------------------------------------------------------------------
    def _handle_notify(self, value_handle, data):
        label = self._handle_label.get(value_handle, f"handle={value_handle}")

        # Prova a capire il tipo dal label o dalla lunghezza
        is_consumer = "consumer" in label.lower() or (len(data) == 3 and data[0] != 0)
        is_mouse    = (value_handle == self._boot_mouse_handle) or "mouse" in label.lower()

        if is_mouse:
            self._decode_mouse(label, data)
        elif len(data) >= 8 and data[1] == 0x00:
            # Report tastiera: [modifier, 0x00, key1..key6]
            self._decode_keyboard(label, data)
        elif len(data) in (2, 3):
            # Probabile Consumer Control: [report_id, usage_lo, usage_hi]
            self._decode_consumer(label, data)
        else:
            # Raw fallback
            print(f"[RAW/{label}] {' '.join(f'{b:02X}' for b in data)}")
            self._log("raw", label, data, {})

    def _decode_keyboard(self, label, data):
        mod      = data[0]
        keycodes = [k for k in data[2:] if k != 0x00]
        if not keycodes:
            return   # key-up, ignora
        chars = [_decode_key(k, mod) for k in keycodes]
        mod_s = _modifier_str(mod)
        print(f"[KEYBOARD/{label}]  modifier={mod_s}  "
              f"keys={[f'0x{k:02X}' for k in keycodes]}  → {chars}")
        self._log("keyboard", label, data,
                  {"modifier": mod, "modifier_str": mod_s,
                   "keycodes": keycodes, "chars": chars})

    def _decode_consumer(self, label, data):
        if len(data) >= 3:
            usage = data[1] | (data[2] << 8)
        elif len(data) == 2:
            usage = data[1]
        else:
            return
        if usage == 0:
            return   # key-up
        name = _CONSUMER_MAP.get(usage, f"usage=0x{usage:04X}")
        print(f"[CONSUMER/{label}]  usage=0x{usage:04X}  → {name}")
        self._log("consumer", label, data, {"usage": usage, "name": name})

    def _decode_mouse(self, label, data):
        # Standard boot mouse: [buttons, x, y] o [buttons, x, y, wheel]
        if len(data) < 3:
            return
        buttons = data[0]
        x       = data[1] if data[1] < 128 else data[1] - 256
        y       = data[2] if data[2] < 128 else data[2] - 256
        wheel   = (data[3] if data[3] < 128 else data[3] - 256) if len(data) > 3 else 0
        if buttons == 0 and x == 0 and y == 0 and wheel == 0:
            return
        print(f"[MOUSE/{label}]  buttons=0x{buttons:02X}  x={x}  y={y}  wheel={wheel}")
        self._log("mouse", label, data,
                  {"buttons": buttons, "x": x, "y": y, "wheel": wheel})

    def _log(self, kind, label, data, decoded):
        entry = {
            "kind":    kind,
            "label":   label,
            "raw_hex": " ".join(f"{b:02X}" for b in data),
            "decoded": decoded,
        }
        self._raw_log.append(entry)

    # -----------------------------------------------------------------------
    # Salvataggio
    # -----------------------------------------------------------------------
    def save_log(self):
        if not self._raw_log:
            print("Nessun evento registrato.")
            return
        try:
            with open(OUTPUT_FILE, "w") as f:
                json.dump(self._raw_log, f)
            print(f"Log salvato in {OUTPUT_FILE} ({len(self._raw_log)} eventi)")
        except Exception as e:
            print(f"Errore salvataggio: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
mapper = HidMapper()
mapper.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

mapper.save_log()
print("Fatto.")
