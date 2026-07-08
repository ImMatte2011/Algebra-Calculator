"""
hardware_setup.py — Hardware factory: reads CONFIG and prepares all peripherals.

This module is the only place that knows about physical pin assignments and
driver class names. Everything it creates is injected into CalculatorApp.

Public API: get_hardware() -> (display, keypad, ble, mode_manager, wdt)
"""

import machine
from config import CONFIG


def get_hardware():
    """Instantiate and configure every hardware peripheral from CONFIG.

    Returns a 5-tuple:
        display      — configured display driver, with .cols/.rows attributes
        keypad       — configured keypad driver
        ble          — BLEBridge instance (matrix) or None (ble_hid, lazy)
        mode_manager — BleModeManager instance or None (always None here)
        wdt          — machine.WDT instance or None if watchdog is disabled
    """

    # -----------------------------------------------------------------------
    # Display
    # -----------------------------------------------------------------------
    if CONFIG["DISPLAY_TYPE"] == "oled":
        from drivers.oled_display import OledDisplay
        display = OledDisplay()
        display.cols = CONFIG["OLED"]["WIDTH"] // 8   # 16 cols with 8 px font
        display.rows = CONFIG["OLED"]["HEIGHT"] // 8  # 8 rows with 8 px font

    else:
        from drivers.lcd_display import LCDDisplay
        lcd_cfg = CONFIG["LCD"]
        display = LCDDisplay(
            scl_pin=lcd_cfg["SCL_PIN"], sda_pin=lcd_cfg["SDA_PIN"],
            i2c_addr=lcd_cfg["I2C_ADDR"],
            cols=lcd_cfg["COLS"], rows=lcd_cfg["ROWS"],
        )
        display.cols = lcd_cfg["COLS"]
        display.rows = lcd_cfg["ROWS"]

    # -----------------------------------------------------------------------
    # Keypad + BLE
    # -----------------------------------------------------------------------
    if CONFIG["KEYPAD_TYPE"] == "ble_hid":
        import ubluetooth
        from drivers.keypad_ble_hid import KeypadBleHid

        # Single BLE radio shared by keypad and the lazily-allocated BLEBridge.
        _ble = ubluetooth.BLE()
        _ble.active(True)

        keypad = KeypadBleHid(ble_instance=_ble, register_irq=False)

        # Expose the raw radio so CalculatorApp can create BLEBridge lazily.
        keypad.ble_radio = _ble

        # Mutable slot: CalculatorApp writes self.ble here after lazy init so
        # the IRQ router below can forward peripheral-role events to the bridge.
        _bridge_ref = [None]
        keypad._bridge_ref = _bridge_ref

        _CENTRAL_EVENTS = frozenset(range(7, 19))

        def _on_ble_irq(event, data):
            if event in _CENTRAL_EVENTS:
                keypad.handle_irq(event, data)
            elif _bridge_ref[0] is not None:
                _bridge_ref[0].handle_irq(event, data)

        _ble.irq(_on_ble_irq)
        keypad.start_connect()

        # BLEBridge and BleModeManager are deferred until the first TX.
        ble          = None
        mode_manager = None

    else:
        from drivers.keypad_matrix import KeypadMatrix
        from ble.ble_bridge import BLEBridge

        kp_cfg = CONFIG["KEYPAD"]
        keypad = KeypadMatrix(
            row_pins=kp_cfg["ROW_PINS"],
            col_pins=kp_cfg["COL_PINS"],
            primary_map=kp_cfg["PRIMARY_MAP"],
            shift_a_map=kp_cfg.get("SHIFT_A_MAP"),
            shift_b_map=kp_cfg.get("SHIFT_B_MAP"),
        )
        ble          = BLEBridge()
        mode_manager = None

    # -----------------------------------------------------------------------
    # Watchdog
    # -----------------------------------------------------------------------
    wdt = (machine.WDT(timeout=CONFIG.get("WATCHDOG_TIMEOUT_MS", 60000))
           if CONFIG.get("ENABLE_WATCHDOG", False) else None)

    return display, keypad, ble, mode_manager, wdt