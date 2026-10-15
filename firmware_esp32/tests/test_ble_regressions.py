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
    ubluetooth.FLAG_WRITE_ENCRYPTED = 16
    ubluetooth.FLAG_READ_ENCRYPTED = 32
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
        self.services = None
        self.read_data = b""

    def config(self, **kwargs):
        self.config_values.update(kwargs)

    def gatts_register_services(self, services):
        self.services = services
        return ((1, 2),)

    def gatts_set_buffer(self, handle, size):
        self.buffers.append((handle, size))

    def gap_advertise(self, interval, payload=None):
        self.advertisements.append((interval, payload))

    def gap_disconnect(self, conn_handle):
        self.disconnects.append(conn_handle)

    def gatts_read(self, handle):
        return self.read_data


def test_bridge_sets_mtu_buffers_and_advertises_idempotently():
    radio = FakeBLE()
    bridge = BLEBridge(ble_instance=radio, register_irq=False)

    assert radio.config_values["mtu"] == 256
    assert radio.config_values["bond"]
    assert radio.config_values["le_secure"]
    expression_flags = radio.services[0][1][0][1]
    result_flags = radio.services[0][1][1][1]
    assert expression_flags & ubluetooth.FLAG_WRITE_ENCRYPTED
    assert result_flags & ubluetooth.FLAG_READ_ENCRYPTED
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
    assert bridge.rx_queue == []
    bridge.start_advertising()
    assert bridge.advertising


def test_bridge_bounds_receive_queue_and_payload_size():
    radio = FakeBLE()
    bridge = BLEBridge(ble_instance=radio, register_irq=False)
    for _ in range(bridge.MAX_RX_QUEUE):
        radio.read_data = b"valid"
        bridge._irq(bridge._IRQ_GATTS_WRITE, (1, bridge.expr_handle))
    radio.read_data = b"overflow"
    bridge._irq(bridge._IRQ_GATTS_WRITE, (1, bridge.expr_handle))
    assert len(bridge.rx_queue) == bridge.MAX_RX_QUEUE

    radio.read_data = b"x" * (bridge.MAX_RX_PAYLOAD + 1)
    bridge.rx_queue.clear()
    bridge._irq(bridge._IRQ_GATTS_WRITE, (1, bridge.expr_handle))
    assert bridge.rx_queue == []


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


def test_keypad_retries_connect_after_missing_disconnect_irq(monkeypatch):
    import drivers.keypad_ble_hid as keypad_module

    class ConnectBLE:
        def __init__(self):
            self.connects = []

        def gap_connect(self, addr_type, addr):
            self.connects.append((addr_type, addr))

    clock = [0]
    monkeypatch.setattr(keypad_module.time, "ticks_ms",
                        lambda: clock[0], raising=False)
    monkeypatch.setattr(keypad_module.time, "ticks_diff",
                        lambda now, then: now - then, raising=False)
    monkeypatch.setattr(keypad_module, "_MAC", "AA:BB:CC:DD:EE:FF")
    keypad = object.__new__(KeypadBleHid)
    keypad._ble = ConnectBLE()
    keypad._phase = "connecting"
    keypad._connect_started_ms = 0
    keypad._last_disconnect_ms = 0
    keypad._reconnect_enabled = True
    keypad._event_queue = []
    keypad.on_state_change = None

    clock[0] = keypad.CONNECT_TIMEOUT_MS + 1
    assert keypad.update() is None
    assert keypad._phase == "disconnected"

    clock[0] += keypad.RECONNECT_DELAY_MS
    assert keypad.update() is None
    assert keypad._phase == "connecting"
    assert keypad._ble.connects == [
        (0, bytes((0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF)))
    ]


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


def test_lcd_render_shows_cursor_and_hides_it_for_result():
    from drivers.lcd_display import LCDDisplay

    class FakeLcd:
        def __init__(self):
            self.calls = []

        def hide_cursor(self):
            self.calls.append(("hide",))

        def blink_cursor_on(self):
            self.calls.append(("blink",))

    display = object.__new__(LCDDisplay)
    display.cols = 16
    display.rows = 2
    display.lcd = FakeLcd()
    display.show_text = lambda text, line: None
    display.set_cursor = lambda x, y=0: display.lcd.calls.append(("cursor", x, y))

    display.render("12345", 3)
    assert ("cursor", 3, 0) in display.lcd.calls
    assert ("blink",) in display.lcd.calls

    display.render("", 0, result="42")
    assert display.lcd.calls[-1] == ("hide",)


def test_oled_cursor_and_wrapped_long_result(monkeypatch):
    machine = sys.modules.get("machine")
    if machine is None:
        machine = types.ModuleType("machine")
        sys.modules["machine"] = machine
    machine.Pin = getattr(machine, "Pin", object)
    machine.SPI = getattr(machine, "SPI", object)
    machine.I2C = getattr(machine, "I2C", object)

    framebuf = types.ModuleType("framebuf")
    framebuf.MONO_VLSB = 0
    sys.modules["framebuf"] = framebuf
    from drivers import oled_display

    class FakeFrameBuffer:
        def __init__(self):
            self.text_calls = []
            self.fill_rect_calls = []

        def fill(self, color):
            pass

        def fill_rect(self, *args):
            self.fill_rect_calls.append(args)

        def text(self, text, x, y, color):
            self.text_calls.append((text, x, y, color))

    display = object.__new__(oled_display.OledDisplay)
    display.width = 128
    display.height = 64
    display._fb = FakeFrameBuffer()
    display.show = lambda: None
    display._draw_glyph_bitmap = lambda bitmap, x, y: None

    display.render("123", 1, status="ready")
    assert (8, 7, 8, 1, 1) in display._fb.fill_rect_calls

    display._fb.text_calls.clear()
    result = "12345678" + "abcdefghijklmnop" * 4
    display.render("", 0, result=result)
    result_rows = [(text, y) for text, x, y, _ in display._fb.text_calls
                   if y in (28, 36, 44)]
    assert [y for _, y in result_rows] == [28, 36, 44]
    assert "".join(text for text, _ in result_rows) == result[8:56]


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
    assert display.lines == [("Ready for input", 0), ("Enter expression", 1)]

    app._handle_input()
    app._handle_input()
    assert app.input_handler.expr == "11"

    app.input_handler.expr = "12345678901234567890"
    app.input_handler.cursor_pos = 18
    app._update_display("0")
    assert display.renders[-1][0:2] == ("12345678901234567890", 18)

    monkeypatch.setattr(sys.modules["main"].time, "sleep_ms",
                        lambda _: None, raising=False)
    app._pending_result[0] = "res:err:RPiOff"
    app._handle_pending_result()
    assert any(args[2] == "ERROR: RPiOff" for args in display.renders)
