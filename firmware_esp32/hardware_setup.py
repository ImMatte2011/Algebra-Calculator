"""
hardware_setup.py — Hardware factory: reads CONFIG and prepares all peripherals.

This module is the only place that knows about physical pin assignments and
driver class names. Everything it creates is injected into CalculatorApp.

Public API: get_hardware() -> (display, keypad, ble, mode_manager, wdt)
"""

import machine
from config import CONFIG
from utils.ble_secret_store import BLESecretStore


def get_hardware():
    """Instantiate and configure every hardware peripheral from CONFIG.

    Returns a 5-tuple:
        display      — configured display driver, with .cols/.rows attributes
        keypad       — configured keypad driver
        ble          — configured BLEBridge instance
        mode_manager — BleModeManager for ble_hid, otherwise None
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
    
    elif CONFIG["DISPLAY_TYPE"] == "tft":
        from drivers.tft_display import TftDisplay
        display = TftDisplay()

    elif CONFIG["DISPLAY_TYPE"] == "tft_remote":
        from drivers.tft_remote_display import RemoteTftDisplay
        display = RemoteTftDisplay()

    elif CONFIG["DISPLAY_TYPE"] == "lcd":
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
        from ble.ble_bridge import BLEBridge
        from ble.ble_mode_manager import BleModeManager

        mac = CONFIG.get("BLE_KP_MAC", "")
        parts = mac.split(":")
        if (len(parts) != 6
                or any(len(part) != 2 or any(
                    char not in "0123456789abcdefABCDEF" for char in part
                ) for part in parts)):
            raise ValueError(
                "Set a valid BLE_KP_MAC in firmware_esp32/settings.py"
            )
        
        # Single BLE radio shared by keypad and the BLEBridge.
        _ble = ubluetooth.BLE()
        if not _ble.active():
            _ble.active(True)

        keypad = KeypadBleHid(ble_instance=_ble, register_irq=False)

        ble = BLEBridge(
            ble_instance=_ble,
            register_irq=False
        )
        secret_store = BLESecretStore()

        mode_manager = BleModeManager(
            ble_bridge=ble,
            keypad_ble=keypad
        )

        _CENTRAL_EVENTS = frozenset(range(7, 19))

        def _on_ble_irq(event, data):
            if event == 29:
                return secret_store.get_secret(*data)
            if event == 30:
                return secret_store.set_secret(*data)

            if event in _CENTRAL_EVENTS:
                keypad.handle_irq(event, data)
            elif event in (28, 31):
                keypad.handle_irq(event, data)
                ble.handle_irq(event, data)
            else:
                ble.handle_irq(event, data)

        _ble.irq(_on_ble_irq)
        keypad.start_connect()

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

    if CONFIG["DISPLAY_TYPE"] == "tft" and CONFIG.get("TOUCH", {}).get("ENABLED", True):
        from drivers.touch_xpt2046 import TouchXpt2046
        from drivers.keypad_touch import TouchKeypadMux
        keypad_out = TouchKeypadMux(
            keypad, display,
            TouchXpt2046(display.spi, display.width, display.height),
        )
    elif (CONFIG["DISPLAY_TYPE"] == "tft_remote"
          and CONFIG.get("TOUCH", {}).get("ENABLED", True)):
        from drivers.tft_remote_display import RemoteTouchKeypadMux
        keypad_out = RemoteTouchKeypadMux(keypad, display.link)
    else:
        keypad_out = keypad

    # -----------------------------------------------------------------------
    # Watchdog
    # -----------------------------------------------------------------------
    wdt = (machine.WDT(timeout=CONFIG.get("WATCHDOG_TIMEOUT_MS", 60000))
           if CONFIG.get("ENABLE_WATCHDOG", False) else None)

    return display, keypad_out, ble, mode_manager, wdt