"""
hardware_setup.py

COMMUNICATION_MODE  KEYPAD_TYPE  SOLVE_MODE  → configurazione bridge
─────────────────────────────────────────────────────────────────────
ble                 ble_hid      —           → BLEBridge + BleModeManager
ble                 matrix       —           → BLEBridge
wifi                ble_hid      direct      → WiFiBridge (no BLE peripheral)
wifi                ble_hid      phone/auto  → WiFiBridge + BLEBridge + ModeManager
wifi                matrix       direct      → WiFiBridge (no BLE)
wifi                matrix       phone/auto  → WiFiBridge + BLEBridge
"""

import machine
from config import CONFIG


def get_hardware():
    comm_mode  = CONFIG.get("COMMUNICATION_MODE", "ble")
    wifi_cfg   = CONFIG.get("WIFI", {})
    solve_mode = wifi_cfg.get("SOLVE_MODE", "auto")
    needs_ble  = (comm_mode == "ble") or (comm_mode == "wifi" and solve_mode in ("auto", "phone"))

    # ---------------------------------------------------------------
    # Display
    # ---------------------------------------------------------------
    if CONFIG["DISPLAY_TYPE"] == "oled":
        from drivers.oled_display import OledDisplay
        display = OledDisplay()
        display.cols = CONFIG["OLED"]["WIDTH"]  // 8
        display.rows = CONFIG["OLED"]["HEIGHT"] // 8
    else:
        from drivers.lcd_display import LCDDisplay
        lcd = CONFIG["LCD"]
        display = LCDDisplay(
            scl_pin=lcd["SCL_PIN"], sda_pin=lcd["SDA_PIN"],
            i2c_addr=lcd["I2C_ADDR"], cols=lcd["COLS"], rows=lcd["ROWS"],
        )
        display.cols = lcd["COLS"]
        display.rows = lcd["ROWS"]

    # ---------------------------------------------------------------
    # BLE HID keypad
    # ---------------------------------------------------------------
    if CONFIG["KEYPAD_TYPE"] == "ble_hid":
        import ubluetooth
        from drivers.keypad_ble_hid import KeypadBleHid

        _ble = ubluetooth.BLE()
        if not _ble.active():
            _ble.active(True)

        keypad = KeypadBleHid(ble_instance=_ble, register_irq=False)
        keypad.ble_radio = _ble

        if needs_ble:
            from ble.ble_bridge import BLEBridge
            from ble.ble_mode_manager import BleModeManager

            ble_bridge  = BLEBridge(ble_instance=_ble, register_irq=False)
            _bridge_ref = [ble_bridge]
            keypad._bridge_ref = _bridge_ref
            mode_manager = BleModeManager(ble_bridge=ble_bridge, keypad_ble=keypad)

            _CENTRAL  = frozenset(range(7, 19))
            _SECURITY = frozenset((28, 29, 30, 31))

            def _on_ble_irq(event, data):
                if event in _CENTRAL:
                    keypad.handle_irq(event, data)
                elif event in _SECURITY:
                    try:    keypad.handle_irq(event, data)
                    except: pass
                    if _bridge_ref[0]:
                        try:    _bridge_ref[0].handle_irq(event, data)
                        except: pass
                elif _bridge_ref[0]:
                    _bridge_ref[0].handle_irq(event, data)

            _ble.irq(_on_ble_irq)

            if comm_mode == "wifi":
                from wifi.wifi_bridge import WiFiBridge
                bridge = WiFiBridge(ble_fallback=ble_bridge)
            else:
                bridge = ble_bridge   # modalità BLE pura

        else:
            # wifi direct: solo IRQ central
            mode_manager = None
            _CENTRAL  = frozenset(range(7, 19))
            _SECURITY = frozenset((28, 29, 30, 31))

            def _on_ble_irq(event, data):
                if event in _CENTRAL or event in _SECURITY:
                    keypad.handle_irq(event, data)

            _ble.irq(_on_ble_irq)
            from wifi.wifi_bridge import WiFiBridge
            bridge = WiFiBridge()

        keypad.start_connect()

    # ---------------------------------------------------------------
    # Matrix keypad
    # ---------------------------------------------------------------
    else:
        from drivers.keypad_matrix import KeypadMatrix
        kp = CONFIG["KEYPAD"]
        keypad = KeypadMatrix(
            row_pins=kp["ROW_PINS"], col_pins=kp["COL_PINS"],
            primary_map=kp["PRIMARY_MAP"],
            shift_a_map=kp.get("SHIFT_A_MAP"),
            shift_b_map=kp.get("SHIFT_B_MAP"),
        )
        mode_manager = None

        if comm_mode == "wifi":
            ble_fallback = None
            if needs_ble:
                from ble.ble_bridge import BLEBridge
                ble_fallback = BLEBridge()   # peripheral puro, no radio sharing
            from wifi.wifi_bridge import WiFiBridge
            bridge = WiFiBridge(ble_fallback=ble_fallback)
        else:
            from ble.ble_bridge import BLEBridge
            bridge = BLEBridge()

    # ---------------------------------------------------------------
    # Watchdog
    # ---------------------------------------------------------------
    wdt = (machine.WDT(timeout=CONFIG.get("WATCHDOG_TIMEOUT_MS", 60000))
           if CONFIG.get("ENABLE_WATCHDOG", False) else None)

    return display, keypad, bridge, mode_manager, wdt