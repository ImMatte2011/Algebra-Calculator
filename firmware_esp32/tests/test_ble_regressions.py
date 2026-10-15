"""Host-side regression tests for BLE drivers and pairing-secret persistence."""

import sys
import time
import os
import tempfile
import types

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import ubluetooth
except ImportError:
    ubluetooth = types.ModuleType("ubluetooth")
    ubluetooth.BLE = object
    ubluetooth.UUID = lambda value: value
    ubluetooth.FLAG_WRITE = 1
    ubluetooth.FLAG_WRITE_NO_RESPONSE = 2
    ubluetooth.FLAG_NOTIFY = 4
    ubluetooth.FLAG_READ = 8
    sys.modules["ubluetooth"] = ubluetooth


from ble.ble_bridge import BLEBridge
from ble.ble_mode_manager import BleModeManager
from drivers.keypad_ble_hid import KeypadBleHid
from utils.ble_secret_store import BLESecretStore


class FakeBLE:
    def __init__(self):
        self.config_values = {}
        self.buffers = []
        self.advertisements = []
        self.disconnects = []

    def config(self, **kwargs):
        self.config_values.update(kwargs)

    def gatts_register_services(self, services):
        return ((1, 2),)

    def gatts_set_buffer(self, handle, size):
        self.buffers.append((handle, size))

    def gap_advertise(self, interval, payload=None):
        self.advertisements.append((interval, payload))

    def gap_disconnect(self, conn_handle):
        self.disconnects.append(conn_handle)

    def gatts_read(self, handle):
        return b""


def test_bridge_sets_mtu_buffers_and_advertises_idempotently():
    radio = FakeBLE()
    bridge = BLEBridge(ble_instance=radio, register_irq=False)

    assert radio.config_values["mtu"] == 256
    assert radio.buffers == [(bridge.expr_handle, 256),
                             (bridge.result_handle, 256)]

    bridge.start_advertising(force=True)
    bridge.start_advertising()
    assert len(radio.advertisements) == 1
    assert radio.advertisements[0][0] == 100_000


def test_bridge_inactivity_requests_real_disconnect_then_readvertises():
    radio = FakeBLE()
    bridge = BLEBridge(ble_instance=radio, register_irq=False,
                       inactivity_timeout=10)
    bridge._irq(bridge._IRQ_CENTRAL_CONNECT, (7, 0, b"\x01\x02\x03\x04\x05\x06"))
    bridge.last_activity = time.time() - 11

    assert bridge.is_connected()
    assert radio.disconnects == []
    bridge.poll()
    assert radio.disconnects == [7]
    assert bridge.is_connected()

    bridge._irq(bridge._IRQ_CENTRAL_DISCONNECT, (7, 0, b""))
    assert not bridge.is_connected()
    assert bridge.needs_advertise
    bridge.start_advertising()
    assert bridge.advertising


def test_mode_manager_uses_absolute_peripheral_timeout():
    class FakeKeypad:
        def __init__(self):
            self.reconnect_enabled = True

        def set_reconnect_enabled(self, enabled):
            self.reconnect_enabled = enabled

    class FakeBridge:
        needs_advertise = False

        def __init__(self):
            self.disconnect_called = False
            self.stop_called = False

        def disconnect(self):
            self.disconnect_called = True

        def stop_advertising(self):
            self.stop_called = True

        def is_connected(self):
            return True

    bridge = FakeBridge()
    keypad = FakeKeypad()
    manager = BleModeManager(bridge, keypad)
    manager._mode = manager.MODE_PERIPHERAL
    manager._peripheral_start = time.time() - 31

    assert manager.poll() == {"timeout": True}
    assert bridge.disconnect_called
    assert bridge.stop_called
    assert keypad.reconnect_enabled


def test_mode_manager_disconnects_actual_hid_connection_and_pauses_reconnect():
    class FakeKeypad:
        _conn = 12
        reconnect_enabled = True

        def set_reconnect_enabled(self, enabled):
            self.reconnect_enabled = enabled

    class FakeBridge:
        def __init__(self):
            self.ble = FakeBLE()

        def start_advertising(self, force=False):
            pass

        def disconnect(self):
            pass

        def stop_advertising(self):
            pass

    bridge = FakeBridge()
    keypad = FakeKeypad()
    manager = BleModeManager(bridge, keypad)

    manager.switch_to_peripheral(("x", "expression", None, None))
    assert bridge.ble.disconnects == [12]
    assert not keypad.reconnect_enabled

    manager.switch_to_central()
    assert keypad.reconnect_enabled


def test_hid_rollover_only_enqueues_new_keycodes():
    keypad = object.__new__(KeypadBleHid)
    keypad._event_queue = []
    keypad._previous_keycodes = set()

    keypad._handle_notify(bytes((1, 0, 0, 4, 0, 0, 0)))
    keypad._handle_notify(bytes((1, 0, 0, 4, 5, 0, 0)))
    assert keypad._event_queue == [(4, 0), (5, 0)]

    keypad._handle_notify(bytes((1, 0, 0, 0, 0, 0, 0)))
    keypad._handle_notify(bytes((1, 0, 0, 4, 0, 0, 0)))
    assert keypad._event_queue[-1] == (4, 0)


def test_secret_store_round_trips_and_enumerates():
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        path = os.path.join(directory, "ble_secrets.json")
        store = BLESecretStore(path)
        assert store.set_secret(1, b"peer-a", b"secret-a")
        assert store.set_secret(1, b"peer-b", b"secret-b")

        reloaded = BLESecretStore(path)
        assert reloaded.get_secret(1, 0, b"peer-a") == b"secret-a"
        assert reloaded.get_secret(1, 1, None) == b"secret-b"
        assert reloaded.get_secret(1, 2, None) is None


def test_matrix_debounces_once_per_press(monkeypatch):
    class FakePin:
        OUT = 0
        IN = 1
        PULL_UP = 2
        instances = {}
        pressed = None

        def __init__(self, pin, mode, pull=None):
            self.pin = pin
            self.mode = mode
            self.state = 1
            self.instances[pin] = self

        def value(self, new_value=None):
            if new_value is not None:
                self.state = new_value
                return
            if self.mode == self.OUT:
                return self.state
            active = self.instances[10].state == 0
            return 0 if active and self.pressed == (0, 0) else 1

    machine = types.ModuleType("machine")
    machine.Pin = FakePin
    sys.modules["machine"] = machine
    sys.modules.pop("drivers.keypad_matrix", None)
    from drivers import keypad_matrix

    clock = [0]
    monkeypatch.setattr(keypad_matrix.time, "ticks_ms",
                        lambda: clock[0], raising=False)
    monkeypatch.setattr(keypad_matrix.time, "ticks_diff",
                        lambda now, then: now - then, raising=False)
    keypad = keypad_matrix.KeypadMatrix(
        row_pins=[10],
        col_pins=[11],
        key_matrix=[["K_1"]],
        primary_map={"K_1": "1"},
    )
    assert keypad.debounce_ms == 50

    FakePin.pressed = (0, 0)
    assert keypad.update() is None
    clock[0] = 49
    assert keypad.update() is None
    clock[0] = 50
    assert keypad.update() == "1"
    clock[0] = 100
    assert keypad.update() is None

    FakePin.pressed = None
    clock[0] = 101
    assert keypad.update() is None
    FakePin.pressed = (0, 0)
    clock[0] = 102
    assert keypad.update() is None
    clock[0] = 152
    assert keypad.update() == "1"


def test_i2c_lcd_initializes_api_and_keeps_backlight_enabled(monkeypatch):
    machine = sys.modules.get("machine")
    if machine is None:
        machine = types.ModuleType("machine")
        sys.modules["machine"] = machine
    machine.I2C = object

    class FakeI2C:
        def __init__(self):
            self.writes = []

        def writeto(self, address, data):
            self.writes.append((address, data[0]))

    from drivers import i2c_lcd

    monkeypatch.setattr(i2c_lcd.time, "sleep_ms", lambda _: None, raising=False)
    lcd = i2c_lcd.I2cLcd(FakeI2C(), 0x27, 2, 16)

    assert (lcd.num_lines, lcd.num_columns) == (2, 16)
    assert all(value & 0x08 for _, value in lcd.i2c.writes)


def test_main_handles_lcd_prompt_error_prefix_and_repeated_keys(monkeypatch):
    from main import CalculatorApp

    class FakeDisplay:
        cols = 16
        rows = 2

        def __init__(self):
            self.lines = []
            self.renders = []

        def show_text(self, text, line):
            self.lines.append((text, line))

        def render(self, *args):
            self.renders.append(args)

    class FakeKeypad:
        def __init__(self):
            self.keys = ["1", "1"]

        def update(self):
            return self.keys.pop(0)

        def is_ready(self):
            return True

        def reset_shift(self):
            pass

    class FakeBridge:
        callback = None

        def start_advertising(self, force=False):
            pass

    display = FakeDisplay()
    app = CalculatorApp(display, FakeKeypad(), FakeBridge(), None, None)
    app._show_waiting_prompt()
    assert display.lines == [("In attesa di", 0), ("  input...", 1)]

    app._handle_input()
    app._handle_input()
    assert app.input_handler.expr == "11"

    monkeypatch.setattr(sys.modules["main"].time, "sleep_ms",
                        lambda _: None, raising=False)
    app._pending_result[0] = "res:err:RPiOff"
    app._handle_pending_result()
    assert any(args[2] == "ERROR: RPiOff" for args in display.renders)
