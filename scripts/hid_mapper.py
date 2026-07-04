"""
BLE HID diagnostics tool for MicroPython ESP32.

Upload this file to the ESP32 as ``main.py`` and run it from a serial
terminal. The tool discovers BLE HID devices, connects to the selected target,
inspects HID reports, enables notifications, decodes common HID events, and
writes a complete JSON diagnostics report.

Configuration is read from ``config.json`` when present. Runtime reports are
written under the configured reports directory and never back into config.
"""

import json
import time
import ubluetooth


TOOL_NAME = "BLE HID Analyzer"
TOOL_VERSION = "2.0.0"
CONFIG_FILE = "config.json"
KNOWN_DEVICES_FILE = "known_devices.json"
DEFAULT_REPORTS_DIRECTORY = "reports"

VERBOSITY_QUIET = 0
VERBOSITY_NORMAL = 1
VERBOSITY_DEBUG = 2
VERBOSITY_NAMES = {
    "QUIET": VERBOSITY_QUIET,
    "NORMAL": VERBOSITY_NORMAL,
    "DEBUG": VERBOSITY_DEBUG,
}

DEFAULT_CONFIG = {
    "auto_scan": True,
    "target_mac": "",
    "device_name": "",
    "verbose": "NORMAL",
    "save_reports": True,
    "reports_directory": DEFAULT_REPORTS_DIRECTORY,
    "overwrite_last_report": True,
    "scan_timeout": 5,
    "connect_timeout": 20,
    "create_config_if_missing": False,
}

_UUID_HID_SERVICE = ubluetooth.UUID(0x1812)
_UUID_HID_REPORT = ubluetooth.UUID(0x2A4D)
_UUID_BOOT_MOUSE = ubluetooth.UUID(0x2A33)
_UUID_REPORT_REF = ubluetooth.UUID(0x2908)
_UUID_CCCD = ubluetooth.UUID(0x2902)

_REPORT_TYPE = {0x01: "INPUT", 0x02: "OUTPUT", 0x03: "FEATURE"}

_HID_KEYMAP = {
    0x04: ("a", "A"), 0x05: ("b", "B"), 0x06: ("c", "C"), 0x07: ("d", "D"),
    0x08: ("e", "E"), 0x09: ("f", "F"), 0x0A: ("g", "G"), 0x0B: ("h", "H"),
    0x0C: ("i", "I"), 0x0D: ("j", "J"), 0x0E: ("k", "K"), 0x0F: ("l", "L"),
    0x10: ("m", "M"), 0x11: ("n", "N"), 0x12: ("o", "O"), 0x13: ("p", "P"),
    0x14: ("q", "Q"), 0x15: ("r", "R"), 0x16: ("s", "S"), 0x17: ("t", "T"),
    0x18: ("u", "U"), 0x19: ("v", "V"), 0x1A: ("w", "W"), 0x1B: ("x", "X"),
    0x1C: ("y", "Y"), 0x1D: ("z", "Z"),
    0x1E: ("1", "!"), 0x1F: ("2", "@"), 0x20: ("3", "#"), 0x21: ("4", "$"),
    0x22: ("5", "%"), 0x23: ("6", "^"), 0x24: ("7", "&"), 0x25: ("8", "*"),
    0x26: ("9", "("), 0x27: ("0", ")"),
    0x28: ("ENTER", "ENTER"), 0x29: ("ESC", "ESC"), 0x2A: ("BKSP", "BKSP"),
    0x2B: ("TAB", "TAB"), 0x2C: ("SPACE", "SPACE"), 0x2D: ("-", "_"),
    0x2E: ("=", "+"), 0x2F: ("[", "{"), 0x30: ("]", "}"), 0x31: ("\\", "|"),
    0x33: (";", ":"), 0x34: ("'", '"'), 0x35: ("`", "~"), 0x36: (",", "<"),
    0x37: (".", ">"), 0x38: ("/", "?"), 0x39: ("CAPS", "CAPS"),
    0x4A: ("HOME", "HOME"), 0x4B: ("PGUP", "PGUP"), 0x4C: ("DEL", "DEL"),
    0x4D: ("END", "END"), 0x4E: ("PGDN", "PGDN"), 0x4F: ("RIGHT", "RIGHT"),
    0x50: ("LEFT", "LEFT"), 0x51: ("DOWN", "DOWN"), 0x52: ("UP", "UP"),
}

_CONSUMER_MAP = {
    0x00E2: "mute",
    0x00E9: "volume_up",
    0x00EA: "volume_down",
    0x00B5: "next_track",
    0x00B6: "prev_track",
    0x00CD: "play_pause",
    0x00B7: "stop",
    0x0070: "brightness_up",
    0x006F: "brightness_down",
    0x019E: "lock",
    0x0221: "search",
    0x0223: "home_browser",
    0x018A: "email",
    0x0192: "calculator",
}


def ticks_ms():
    """Return monotonic milliseconds on MicroPython and CPython-like runtimes."""
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def ticks_diff(new, old):
    """Return elapsed milliseconds on MicroPython and CPython-like runtimes."""
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(new, old)
    return new - old


def sleep_ms(ms):
    """Sleep for a millisecond interval."""
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(ms)
    else:
        time.sleep(ms / 1000)


def timestamp_string():
    """Return a filesystem-friendly timestamp."""
    t = time.localtime()
    return "%04d-%02d-%02d_%02d-%02d-%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])


def iso_timestamp():
    """Return a readable timestamp for JSON reports."""
    t = time.localtime()
    return "%04d-%02d-%02dT%02d:%02d:%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])


def bytes_to_hex(data):
    """Return bytes as a compact uppercase hex string."""
    return " ".join("%02X" % b for b in data)


def addr_to_str(addr):
    """Convert a BLE address byte sequence to human-readable MAC format."""
    return ":".join("%02X" % b for b in bytes(addr))


def str_to_addr(mac):
    """Convert a MAC string to BLE address bytes."""
    return bytes(int(part, 16) for part in mac.split(":"))


def uuid_to_str(uuid):
    """Convert a MicroPython UUID object to a stable string."""
    return str(uuid)


def shifted(modifier):
    """Return True when either shift modifier is active."""
    return bool(modifier & 0x22)


def modifier_str(modifier):
    """Format HID keyboard modifier bits."""
    parts = []
    if modifier & 0x22:
        parts.append("SHIFT")
    if modifier & 0x11:
        parts.append("CTRL")
    if modifier & 0x44:
        parts.append("ALT")
    if modifier & 0x88:
        parts.append("GUI")
    return "+".join(parts) if parts else "none"


def decode_key(keycode, modifier):
    """Decode a HID keyboard keycode using the local lookup table."""
    if keycode == 0:
        return None
    entry = _HID_KEYMAP.get(keycode)
    if entry:
        return entry[1] if shifted(modifier) else entry[0]
    return "0x%02X" % keycode


class ConfigManager:
    """Load user configuration without mixing it with generated data."""

    def __init__(self, filename=CONFIG_FILE):
        self.filename = filename

    def load(self):
        config = dict(DEFAULT_CONFIG)
        try:
            with open(self.filename, "r") as file_obj:
                loaded = json.load(file_obj)
            if isinstance(loaded, dict):
                config.update(loaded)
        except OSError:
            if config.get("create_config_if_missing"):
                self.create_default()
        except ValueError:
            pass
        config["verbose"] = str(config.get("verbose", "NORMAL")).upper()
        if config["verbose"] not in VERBOSITY_NAMES:
            config["verbose"] = "NORMAL"
        return config

    def create_default(self):
        """Create a default config file only when explicitly enabled."""
        try:
            with open(self.filename, "w") as file_obj:
                json.dump(DEFAULT_CONFIG, file_obj)
        except OSError:
            pass


class KnownDevicesStore:
    """Persist user-approved known devices outside the main config file."""

    def __init__(self, filename=KNOWN_DEVICES_FILE):
        self.filename = filename
        self.devices = self.load()

    def load(self):
        try:
            with open(self.filename, "r") as file_obj:
                data = json.load(file_obj)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def find_by_mac(self, mac):
        for device in self.devices:
            if str(device.get("mac", "")).upper() == mac.upper():
                return device
        return None

    def add(self, name, mac):
        if self.find_by_mac(mac):
            return False
        self.devices.append({"name": name or "Unknown", "mac": mac})
        self.save()
        return True

    def save(self):
        try:
            with open(self.filename, "w") as file_obj:
                json.dump(self.devices, file_obj)
            return True
        except OSError:
            return False


class ConsoleLogger:
    """Verbosity-aware console output."""

    def __init__(self, level_name="NORMAL"):
        self.level = VERBOSITY_NAMES.get(str(level_name).upper(), VERBOSITY_NORMAL)

    def quiet(self, message):
        self._print(message, VERBOSITY_QUIET)

    def normal(self, message):
        self._print(message, VERBOSITY_NORMAL)

    def debug(self, message):
        self._print(message, VERBOSITY_DEBUG)

    def _print(self, message, level):
        if self.level >= level:
            print(message)


class DiagnosticsReport:
    """Collect enough data to reconstruct the BLE HID debugging session."""

    def __init__(self, config):
        self.config = config
        self.data = {
            "timestamp": iso_timestamp(),
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "device": {},
            "diagnostics": {
                "connection": False,
                "hid_service": False,
                "characteristics": False,
                "descriptors": False,
                "report_reference": False,
                "cccd": False,
                "notifications": False,
                "parsing": False,
            },
            "services": [],
            "characteristics": [],
            "descriptors": [],
            "reports": [],
            "events": [],
            "summary": {},
        }
        self.stats = {
            "notifications": 0,
            "keyboard_reports": 0,
            "consumer_reports": 0,
            "mouse_reports": 0,
            "vendor_reports": 0,
            "unknown_reports": 0,
            "raw_reports": 0,
            "cccd_enabled": 0,
            "cccd_total": 0,
            "report_characteristics": 0,
        }
        self.failures = []

    def set_device(self, name=None, mac=None, rssi=None, addr_type=None, known=False):
        self.data["device"] = {
            "name": name or "",
            "mac": mac or "",
            "rssi": rssi,
            "addr_type": addr_type,
            "known": bool(known),
        }

    def mark(self, key, ok=True, failure=None):
        self.data["diagnostics"][key] = bool(ok)
        if not ok and failure:
            self.failures.append(failure)

    def add_service(self, start_handle, end_handle, uuid):
        self.data["services"].append({
            "start_handle": start_handle,
            "end_handle": end_handle,
            "uuid": uuid_to_str(uuid),
            "is_hid": uuid == _UUID_HID_SERVICE,
        })

    def add_characteristic(self, def_handle, value_handle, properties, uuid):
        self.data["characteristics"].append({
            "definition_handle": def_handle,
            "value_handle": value_handle,
            "properties": properties,
            "uuid": uuid_to_str(uuid),
        })

    def add_descriptor(self, value_handle, descriptor_handle, uuid):
        self.data["descriptors"].append({
            "value_handle": value_handle,
            "handle": descriptor_handle,
            "uuid": uuid_to_str(uuid),
            "kind": self.descriptor_kind(uuid),
        })

    def add_report_reference(self, value_handle, descriptor_handle, report_id, report_type, raw):
        report = {
            "value_handle": value_handle,
            "descriptor_handle": descriptor_handle,
            "report_id": report_id,
            "report_type": report_type,
            "category": "Unknown",
            "raw_hex": bytes_to_hex(raw),
            "cccd_handle": None,
            "cccd_enabled": False,
        }
        self.data["reports"].append(report)
        return report

    def update_report_category(self, value_handle, category):
        report = self.report_by_handle(value_handle)
        if report:
            report["category"] = category

    def set_report_cccd(self, value_handle, cccd_handle, enabled):
        report = self.report_by_handle(value_handle)
        if report:
            report["cccd_handle"] = cccd_handle
            report["cccd_enabled"] = bool(enabled)

    def report_by_handle(self, value_handle):
        for report in self.data["reports"]:
            if report.get("value_handle") == value_handle:
                return report
        return None

    def add_event(self, event):
        self.data["events"].append(event)
        self.stats["notifications"] += 1
        kind = event.get("kind", "unknown")
        if kind == "keyboard":
            self.stats["keyboard_reports"] += 1
        elif kind == "consumer":
            self.stats["consumer_reports"] += 1
        elif kind == "mouse":
            self.stats["mouse_reports"] += 1
        elif kind == "vendor":
            self.stats["vendor_reports"] += 1
        elif kind == "unknown":
            self.stats["unknown_reports"] += 1
        elif kind == "raw":
            self.stats["raw_reports"] += 1

    def descriptor_kind(self, uuid):
        if uuid == _UUID_CCCD:
            return "CCCD"
        if uuid == _UUID_REPORT_REF:
            return "Report Reference"
        return "Descriptor"

    def finalize(self):
        self.stats["report_characteristics"] = len(self.data["reports"])
        self.data["summary"] = {
            "stats": dict(self.stats),
            "failures": list(self.failures),
            "result": "PASS" if not self.failures and self._required_checks_passed() else "FAIL",
        }
        return self.data

    def _required_checks_passed(self):
        checks = self.data["diagnostics"]
        required = ("connection", "hid_service", "characteristics", "descriptors", "report_reference", "cccd")
        for key in required:
            if not checks.get(key):
                return False
        return True


class ReportWriter:
    """Write session reports to a dedicated reports directory."""

    def __init__(self, config):
        self.enabled = bool(config.get("save_reports", True))
        self.directory = config.get("reports_directory") or DEFAULT_REPORTS_DIRECTORY

    def save(self, report):
        if not self.enabled:
            return None
        self._ensure_directory(self.directory)
        saved = []
        timestamped = self._unique_report_path(timestamp_string())
        self._write_json(timestamped, report)
        saved.append(timestamped)
        last_path = self.directory + "/last_report.json"
        self._write_json(last_path, report)
        saved.append(last_path)
        return saved

    def _ensure_directory(self, directory):
        try:
            import os
            os.mkdir(directory)
        except OSError:
            pass

    def _write_json(self, filename, data):
        with open(filename, "w") as file_obj:
            json.dump(data, file_obj)

    def _unique_report_path(self, stamp):
        base = self.directory + "/" + stamp
        candidate = base + ".json"
        suffix = 1
        while self._exists(candidate):
            candidate = "%s_%02d.json" % (base, suffix)
            suffix += 1
        return candidate

    def _exists(self, filename):
        try:
            import os
            os.stat(filename)
            return True
        except OSError:
            return False


class HIDReportParser:
    """Decode common BLE HID notifications and preserve every unknown report."""

    def parse(self, value_handle, data, label, category, boot_mouse_handle=None):
        is_mouse = category == "Mouse" or value_handle == boot_mouse_handle
        is_consumer = category == "Consumer Control"
        is_keyboard = category == "Keyboard"
        if is_mouse:
            parsed = self._parse_mouse(data)
            if parsed:
                return parsed
        if is_keyboard or (len(data) >= 8 and data[1] == 0x00):
            parsed = self._parse_keyboard(data)
            if parsed:
                return parsed
        if is_consumer or len(data) in (2, 3):
            parsed = self._parse_consumer(data)
            if parsed:
                return parsed
        return {
            "kind": "raw" if category == "Unknown" else "vendor",
            "label": label,
            "raw_hex": bytes_to_hex(data),
            "decoded": {"category": category, "length": len(data)},
            "display": "[RAW/%s] %s" % (label, bytes_to_hex(data)),
            "quiet": "RAW %s" % bytes_to_hex(data),
        }

    def _parse_keyboard(self, data):
        if len(data) < 3:
            return None
        modifier = data[0]
        keycodes = [key for key in data[2:] if key != 0x00]
        if not keycodes:
            return None
        chars = [decode_key(key, modifier) for key in keycodes]
        mod_text = modifier_str(modifier)
        return {
            "kind": "keyboard",
            "label": "Keyboard",
            "raw_hex": bytes_to_hex(data),
            "decoded": {
                "modifier": modifier,
                "modifier_str": mod_text,
                "keycodes": keycodes,
                "chars": chars,
            },
            "display": "[KEYBOARD] modifier=%s keys=%s -> %s" % (
                mod_text,
                ["0x%02X" % key for key in keycodes],
                chars,
            ),
            "quiet": " + ".join(chars),
        }

    def _parse_consumer(self, data):
        if len(data) >= 3:
            usage = data[1] | (data[2] << 8)
        elif len(data) == 2:
            usage = data[1]
        else:
            return None
        if usage == 0:
            return None
        name = _CONSUMER_MAP.get(usage, "usage=0x%04X" % usage)
        return {
            "kind": "consumer",
            "label": "Consumer Control",
            "raw_hex": bytes_to_hex(data),
            "decoded": {"usage": usage, "name": name},
            "display": "[CONSUMER] usage=0x%04X -> %s" % (usage, name),
            "quiet": name.upper(),
        }

    def _parse_mouse(self, data):
        if len(data) < 3:
            return None
        buttons = data[0]
        x = self._signed(data[1])
        y = self._signed(data[2])
        wheel = self._signed(data[3]) if len(data) > 3 else 0
        if buttons == 0 and x == 0 and y == 0 and wheel == 0:
            return None
        quiet = "MOUSE"
        if wheel > 0:
            quiet = "KNOB CW"
        elif wheel < 0:
            quiet = "KNOB CCW"
        return {
            "kind": "mouse",
            "label": "Mouse",
            "raw_hex": bytes_to_hex(data),
            "decoded": {"buttons": buttons, "x": x, "y": y, "wheel": wheel},
            "display": "[MOUSE] buttons=0x%02X x=%d y=%d wheel=%d" % (buttons, x, y, wheel),
            "quiet": quiet,
        }

    def _signed(self, value):
        return value if value < 128 else value - 256


class BLEHIDAnalyzer:
    """Coordinate BLE scan, discovery, notifications, parsing, and reporting."""

    _IRQ_SCAN_RESULT = 5
    _IRQ_SCAN_DONE = 6
    _IRQ_PERIPHERAL_CONNECT = 7
    _IRQ_PERIPHERAL_DISCONNECT = 8
    _IRQ_GATTC_SERVICE_RESULT = 9
    _IRQ_GATTC_SERVICE_DONE = 10
    _IRQ_GATTC_CHARACTERISTIC_RESULT = 11
    _IRQ_GATTC_CHARACTERISTIC_DONE = 12
    _IRQ_GATTC_DESCRIPTOR_RESULT = 13
    _IRQ_GATTC_DESCRIPTOR_DONE = 14
    _IRQ_GATTC_READ_RESULT = 15
    _IRQ_GATTC_WRITE_DONE = 17
    _IRQ_GATTC_NOTIFY = 18

    def __init__(self, target_mac=None, config=None):
        self.config = config or ConfigManager().load()
        self.target_mac = target_mac or self.config.get("target_mac") or ""
        self.logger = ConsoleLogger(self.config.get("verbose", "NORMAL"))
        self.known_devices = KnownDevicesStore()
        self.report = DiagnosticsReport(self.config)
        self.report_writer = ReportWriter(self.config)
        self.parser = HIDReportParser()

        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)

        self._conn = None
        self._phase = "idle"
        self._event_queue = []
        self._scan_results = []
        self._target = None
        self._hid_service = None
        self._all_services = []
        self._report_chars = []
        self._boot_mouse_handle = None
        self._char_descriptors = []
        self._current_desc_vh = None
        self._current_char_idx = 0
        self._cccd_queue = []
        self._ref_queue = []
        self._ref_read_pending = None
        self._handle_label = {}
        self._handle_category = {}

    def start(self):
        """Start analysis by target MAC or by BLE scan selection."""
        self.logger.normal("%s v%s" % (TOOL_NAME, TOOL_VERSION))
        if self.target_mac:
            self._target = {"mac": self.target_mac.upper(), "name": self.config.get("device_name", ""), "rssi": None, "addr_type": 0}
            self._connect_selected_target()
        elif self.config.get("auto_scan", True):
            self.scan_and_select()
        else:
            raise ValueError("No target MAC configured and auto_scan is disabled")

    def scan_and_select(self):
        """Scan for nearby BLE devices and ask the user which one to inspect."""
        timeout_ms = int(self.config.get("scan_timeout", 5)) * 1000
        self._scan_results = []
        self._phase = "scanning"
        self.logger.normal("Scanning for BLE devices...")
        self.ble.gap_scan(timeout_ms, 30000, 30000)
        start = ticks_ms()
        while self._phase == "scanning" and ticks_diff(ticks_ms(), start) < timeout_ms + 1000:
            self.process_events()
            sleep_ms(100)
        if not self._scan_results:
            self.report.mark("connection", False, "scan_found_no_devices")
            raise RuntimeError("No BLE devices found")
        self._print_scan_results()
        index = self._ask_device_index()
        self._target = self._scan_results[index]
        self._handle_known_device_choice(self._target)
        self._connect_selected_target()

    def run_forever(self):
        """Process queued BLE events until interrupted."""
        try:
            while True:
                self.process_events()
                sleep_ms(50)
        except KeyboardInterrupt:
            pass
        self.process_events()
        self.finish()

    def finish(self):
        """Save the report and print the final diagnostics summary."""
        self.process_events()
        final_report = self.report.finalize()
        saved = None
        try:
            saved = self.report_writer.save(final_report)
        except Exception as exc:
            self.report.failures.append("json_save_failed:%s" % exc)
            self.report.finalize()
        self._print_summary(saved)

    def save_log(self):
        """Backward-compatible save method for older manual workflows."""
        self.finish()

    def process_events(self):
        """Drain the IRQ event queue outside the BLE interrupt context."""
        while self._event_queue:
            item = self._event_queue.pop(0)
            kind = item[0]
            payload = item[1]
            if kind == "log":
                level, message = payload
                if level == "debug":
                    self.logger.debug(message)
                elif level == "normal":
                    self.logger.normal(message)
                else:
                    self.logger.quiet(message)
            elif kind == "notify":
                value_handle, data = payload
                self._process_notify(value_handle, data)

    def _irq(self, event, data):
        if event == self._IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            self._record_scan_result(addr_type, bytes(addr), adv_type, rssi, bytes(adv_data))
        elif event == self._IRQ_SCAN_DONE:
            self._phase = "scan_done"
        elif event == self._IRQ_PERIPHERAL_CONNECT:
            conn, addr_type, addr = data
            self._conn = conn
            self._phase = "discover_services"
            self.report.mark("connection", True)
            self._queue_log("normal", "Connected. Discovering services...")
            self.ble.gattc_discover_services(conn)
        elif event == self._IRQ_PERIPHERAL_DISCONNECT:
            self._conn = None
            self._phase = "idle"
            self._queue_log("normal", "Disconnected.")
        elif event == self._IRQ_GATTC_SERVICE_RESULT:
            conn, start_handle, end_handle, uuid = data
            uuid_obj = ubluetooth.UUID(uuid)
            self._all_services.append((start_handle, end_handle, uuid_obj))
            self.report.add_service(start_handle, end_handle, uuid_obj)
            self._queue_log("debug", "Service %s handles=%d-%d" % (uuid_to_str(uuid_obj), start_handle, end_handle))
        elif event == self._IRQ_GATTC_SERVICE_DONE:
            self._on_services_done()
        elif event == self._IRQ_GATTC_CHARACTERISTIC_RESULT:
            conn, def_handle, value_handle, props, uuid = data
            uuid_obj = ubluetooth.UUID(uuid)
            self.report.add_characteristic(def_handle, value_handle, props, uuid_obj)
            self._queue_log("debug", "Characteristic %s def=%d value=%d props=0x%02X" % (
                uuid_to_str(uuid_obj), def_handle, value_handle, props))
            if uuid_obj == _UUID_HID_REPORT:
                self._report_chars.append((def_handle, value_handle))
            elif uuid_obj == _UUID_BOOT_MOUSE:
                self._boot_mouse_handle = value_handle
                self._handle_category[value_handle] = "Mouse"
                self._handle_label[value_handle] = "INPUT Mouse"
        elif event == self._IRQ_GATTC_CHARACTERISTIC_DONE:
            self._on_characteristics_done()
        elif event == self._IRQ_GATTC_DESCRIPTOR_RESULT:
            conn, descriptor_handle, uuid = data
            uuid_obj = ubluetooth.UUID(uuid)
            self.report.add_descriptor(self._current_desc_vh, descriptor_handle, uuid_obj)
            if uuid_obj == _UUID_CCCD:
                self._char_descriptors.append(("cccd", descriptor_handle, self._current_desc_vh))
            elif uuid_obj == _UUID_REPORT_REF:
                self._char_descriptors.append(("ref", descriptor_handle, self._current_desc_vh))
            self._queue_log("debug", "Descriptor %s handle=%d value_handle=%s" % (
                uuid_to_str(uuid_obj), descriptor_handle, self._current_desc_vh))
        elif event == self._IRQ_GATTC_DESCRIPTOR_DONE:
            self._current_char_idx += 1
            self._discover_next_char_descriptors()
        elif event == self._IRQ_GATTC_READ_RESULT:
            conn, descriptor_handle, data_bytes = data
            self._on_report_reference_read(descriptor_handle, bytes(data_bytes))
        elif event == self._IRQ_GATTC_WRITE_DONE:
            conn, value_handle, status = data
            self._on_cccd_write_done(value_handle, status)
        elif event == self._IRQ_GATTC_NOTIFY:
            conn, value_handle, notify_data = data
            self._event_queue.append(("notify", (value_handle, bytes(notify_data))))

    def _connect_selected_target(self):
        mac = self._target.get("mac")
        self.report.set_device(
            name=self._target.get("name", ""),
            mac=mac,
            rssi=self._target.get("rssi"),
            addr_type=self._target.get("addr_type", 0),
            known=bool(self.known_devices.find_by_mac(mac)),
        )
        self.logger.normal("Connecting to %s..." % mac)
        self._phase = "connecting"
        self.ble.gap_connect(self._target.get("addr_type", 0), str_to_addr(mac))
        start = ticks_ms()
        timeout_ms = int(self.config.get("connect_timeout", 20)) * 1000
        while self._phase == "connecting" and ticks_diff(ticks_ms(), start) < timeout_ms:
            self.process_events()
            sleep_ms(100)
        if self._phase == "connecting":
            self.report.mark("connection", False, "connection_timeout")
            raise RuntimeError("Connection timeout")

    def _record_scan_result(self, addr_type, addr, adv_type, rssi, adv_data):
        mac = addr_to_str(addr)
        name = self._adv_name(adv_data)
        for item in self._scan_results:
            if item["mac"] == mac:
                if name and not item.get("name"):
                    item["name"] = name
                item["rssi"] = rssi
                return
        known = self.known_devices.find_by_mac(mac)
        self._scan_results.append({
            "name": name or (known.get("name") if known else ""),
            "mac": mac,
            "rssi": rssi,
            "addr_type": addr_type,
            "adv_type": adv_type,
            "known": bool(known),
        })

    def _adv_name(self, adv_data):
        index = 0
        while index + 1 < len(adv_data):
            length = adv_data[index]
            if length == 0:
                break
            ad_type = adv_data[index + 1]
            if ad_type in (0x08, 0x09):
                try:
                    return bytes(adv_data[index + 2:index + 1 + length]).decode("utf-8")
                except Exception:
                    return ""
            index += 1 + length
        return ""

    def _print_scan_results(self):
        self.logger.normal("")
        self.logger.normal("Found BLE devices:")
        for index, device in enumerate(self._scan_results):
            known = " known" if device.get("known") else ""
            self.logger.normal("[%d]%s" % (index, known))
            self.logger.normal(device.get("name") or "Unknown")
            self.logger.normal("MAC %s" % device.get("mac"))
            self.logger.normal("RSSI %s" % device.get("rssi"))
            self.logger.normal("")

    def _ask_device_index(self):
        while True:
            try:
                value = input("Select device index: ")
                index = int(value)
                if 0 <= index < len(self._scan_results):
                    return index
            except Exception:
                pass
            print("Invalid selection.")

    def _handle_known_device_choice(self, device):
        if self.known_devices.find_by_mac(device["mac"]):
            self.logger.normal("Known device selected.")
            return
        try:
            answer = input("Save this device to known_devices.json? [y/N]: ")
            if answer.lower().startswith("y"):
                self.known_devices.add(device.get("name") or "Unknown", device["mac"])
        except Exception:
            pass

    def _on_services_done(self):
        hid = [(start, end) for start, end, uuid in self._all_services if uuid == _UUID_HID_SERVICE]
        if not hid:
            self.report.mark("hid_service", False, "hid_service_not_found")
            self._queue_log("normal", "ERROR: HID service 0x1812 not found.")
            return
        self._hid_service = hid[0]
        self.report.mark("hid_service", True)
        start, end = self._hid_service
        self._phase = "discover_chars"
        self._queue_log("normal", "HID service found (%d-%d). Discovering characteristics..." % (start, end))
        self.ble.gattc_discover_characteristics(self._conn, start, end)

    def _on_characteristics_done(self):
        self.report.mark("characteristics", len(self._report_chars) > 0, "report_characteristics_not_found")
        self._queue_log("normal", "%d Report characteristics found%s" % (
            len(self._report_chars),
            ", Boot Mouse handle=%d" % self._boot_mouse_handle if self._boot_mouse_handle else "",
        ))
        self._phase = "discover_descriptors"
        self._current_char_idx = 0
        self._discover_next_char_descriptors()

    def _discover_next_char_descriptors(self):
        if self._current_char_idx >= len(self._report_chars):
            self._finish_discovery()
            return
        def_handle, value_handle = self._report_chars[self._current_char_idx]
        self._current_desc_vh = value_handle
        if self._current_char_idx + 1 < len(self._report_chars):
            end_handle = self._report_chars[self._current_char_idx + 1][0] - 1
        else:
            end_handle = self._hid_service[1]
        self.ble.gattc_discover_descriptors(self._conn, def_handle, end_handle)

    def _finish_discovery(self):
        self._cccd_queue = [(vh, handle) for kind, handle, vh in self._char_descriptors if kind == "cccd" and handle is not None]
        self._ref_queue = [(vh, handle) for kind, handle, vh in self._char_descriptors if kind == "ref" and handle is not None]
        self.report.stats["cccd_total"] = len(self._cccd_queue)
        self.report.mark("descriptors", len(self._char_descriptors) > 0, "descriptors_not_found")
        self._queue_log("normal", "%d CCCD, %d Report Reference descriptors" % (len(self._cccd_queue), len(self._ref_queue)))
        self._read_next_report_ref()

    def _read_next_report_ref(self):
        if self._ref_queue:
            value_handle, descriptor_handle = self._ref_queue.pop(0)
            self._ref_read_pending = (value_handle, descriptor_handle)
            self.ble.gattc_read(self._conn, descriptor_handle)
        else:
            self.report.mark("report_reference", len(self.data_reports()) > 0, "report_reference_not_found")
            self._print_detected_reports()
            self._enable_next_cccd()

    def _on_report_reference_read(self, descriptor_handle, data):
        if self._ref_read_pending is None:
            return
        value_handle, ref_handle = self._ref_read_pending
        if len(data) >= 2:
            report_id = data[0]
            report_type = _REPORT_TYPE.get(data[1], "0x%02X" % data[1])
            category = self._detect_category(report_id, report_type, value_handle)
            label = "%s %s id=%d" % (report_type, category, report_id)
            self._handle_label[value_handle] = label
            self._handle_category[value_handle] = category
            report = self.report.add_report_reference(value_handle, ref_handle, report_id, report_type, data)
            report["category"] = category
            self._queue_log("normal", "handle=%d -> %s" % (value_handle, label))
        else:
            self._queue_log("debug", "Short Report Reference on descriptor=%d raw=%s" % (descriptor_handle, bytes_to_hex(data)))
        self._ref_read_pending = None
        self._read_next_report_ref()

    def _detect_category(self, report_id, report_type, value_handle):
        if value_handle == self._boot_mouse_handle:
            return "Mouse"
        # Common convention for compact HID devices. Unknown data is still preserved.
        if report_type == "INPUT":
            if report_id in (1, 0):
                return "Keyboard"
            if report_id == 2:
                return "Consumer Control"
            if report_id == 3:
                return "Mouse"
        if report_type in ("OUTPUT", "FEATURE"):
            return "Vendor Specific"
        return "Vendor Specific"

    def _print_detected_reports(self):
        self._queue_log("normal", "")
        self._queue_log("normal", "Detected reports")
        for report in self.data_reports():
            self._queue_log("normal", "%s %s" % (report.get("report_type"), report.get("category")))

    def data_reports(self):
        return self.report.data["reports"]

    def _enable_next_cccd(self):
        if self._cccd_queue:
            value_handle, descriptor_handle = self._cccd_queue.pop(0)
            label = self._handle_label.get(value_handle, "handle=%d" % value_handle)
            self._pending_cccd = (value_handle, descriptor_handle)
            self._queue_log("debug", "Enabling notification for %s (cccd=%d)" % (label, descriptor_handle))
            self.ble.gattc_write(self._conn, descriptor_handle, b"\x01\x00", 1)
        else:
            self._phase = "ready"
            self.report.mark("cccd", self.report.stats["cccd_enabled"] > 0, "cccd_enable_failed")
            self._queue_log("normal", "")
            self._queue_log("normal", "=" * 55)
            self._queue_log("normal", "READY - press keys, buttons, knobs, or controls")
            self._queue_log("normal", "Press Ctrl+C to stop and save the diagnostics report")
            self._queue_log("normal", "=" * 55)
            self._queue_log("normal", "")

    def _on_cccd_write_done(self, descriptor_handle, status):
        pending = getattr(self, "_pending_cccd", None)
        if pending:
            value_handle, cccd_handle = pending
            ok = status == 0
            if ok:
                self.report.stats["cccd_enabled"] += 1
            self.report.set_report_cccd(value_handle, cccd_handle, ok)
            self._queue_log("debug", "CCCD write handle=%d status=%s" % (cccd_handle, status))
        self._pending_cccd = None
        self._enable_next_cccd()

    def _process_notify(self, value_handle, data):
        label = self._handle_label.get(value_handle, "handle=%d" % value_handle)
        category = self._handle_category.get(value_handle, "Unknown")
        self.logger.debug("Notify RAW handle=%d %s" % (value_handle, bytes_to_hex(data)))
        event = self.parser.parse(value_handle, data, label, category, self._boot_mouse_handle)
        inferred = self._category_from_event(event.get("kind"))
        if inferred and category in ("Unknown", "Vendor Specific"):
            category = inferred
            self._handle_category[value_handle] = category
            self.report.update_report_category(value_handle, category)
            event["category"] = category
        event["timestamp_ms"] = ticks_ms()
        event["value_handle"] = value_handle
        event["label"] = label
        event["category"] = category
        self.report.add_event(event)
        self.report.mark("notifications", True)
        if event.get("kind") != "raw":
            self.report.mark("parsing", True)
        if self.logger.level == VERBOSITY_QUIET:
            self.logger.quiet(event.get("quiet", event.get("display", "")))
        else:
            self.logger.normal("%s %s" % (event.get("display", ""), "(%s)" % label if self.logger.level >= VERBOSITY_NORMAL else ""))

    def _queue_log(self, level, message):
        self._event_queue.append(("log", (level, message)))

    def _category_from_event(self, kind):
        if kind == "keyboard":
            return "Keyboard"
        if kind == "consumer":
            return "Consumer Control"
        if kind == "mouse":
            return "Mouse"
        return None

    def _print_summary(self, saved_paths):
        stats = self.report.stats
        summary = self.report.data.get("summary", {})
        device = self.report.data.get("device", {})
        diagnostics = self.report.data.get("diagnostics", {})
        saved = "yes" if saved_paths else "no"
        print("")
        print("=====================================")
        print("BLE HID TEST SUMMARY")
        print("=====================================")
        print("Device")
        print(device.get("name") or device.get("mac") or "Unknown")
        print("Connection")
        print("OK" if diagnostics.get("connection") else "FAIL")
        print("Services")
        print("HID found" if diagnostics.get("hid_service") else "HID missing")
        print("Report characteristics")
        print(stats.get("report_characteristics", 0))
        print("CCCD enabled")
        print("%d/%d" % (stats.get("cccd_enabled", 0), stats.get("cccd_total", 0)))
        print("Notifications")
        print(stats.get("notifications", 0))
        print("Keyboard reports")
        print(stats.get("keyboard_reports", 0))
        print("Consumer reports")
        print(stats.get("consumer_reports", 0))
        print("Mouse reports")
        print(stats.get("mouse_reports", 0))
        print("Unknown reports")
        print(stats.get("unknown_reports", 0) + stats.get("raw_reports", 0))
        print("JSON saved")
        print(saved)
        if saved_paths:
            for path in saved_paths:
                print(path)
        print("RESULT")
        print(summary.get("result", "FAIL"))
        if summary.get("failures"):
            print("Failures")
            for failure in summary["failures"]:
                print(failure)
        print("=====================================")


# Backward-compatible class name for existing workflows.
HidMapper = BLEHIDAnalyzer


def main():
    analyzer = BLEHIDAnalyzer()
    try:
        analyzer.start()
        analyzer.run_forever()
    except Exception as exc:
        analyzer.report.failures.append(str(exc))
        print("ERROR: %s" % exc)
        analyzer.finish()


if __name__ == "__main__":
    main()
