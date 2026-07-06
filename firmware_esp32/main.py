"""
main.py — Entry point for the ESP32 firmware (Algebra Calculator).

Initializes the display, keypad, and BLE based on CONFIG["DISPLAY_TYPE"] and
CONFIG["KEYPAD_TYPE"]: no hardware-specific code here, only orchestration logic.
"""

import time
from config import CONFIG
from core.input_handler import InputHandler
from drivers.display_scroller import TextScroller
from drivers.keypad_base import KeypadAction

# ---------------------------------------------------------------------------
# Display factory
# ---------------------------------------------------------------------------
if CONFIG["DISPLAY_TYPE"] == "oled":
    from drivers.oled_display import OledDisplay
    display = OledDisplay()
    DISPLAY_COLS = CONFIG["OLED"]["WIDTH"] // 8   # 16 col con font 8px
    DISPLAY_ROWS = CONFIG["OLED"]["HEIGHT"] // 8  # 8 righe

else:
    from drivers.lcd_display import LCDDisplay
    lcd_cfg = CONFIG["LCD"]
    display = LCDDisplay(
        scl_pin=lcd_cfg["SCL_PIN"], sda_pin=lcd_cfg["SDA_PIN"],
        i2c_addr=lcd_cfg["I2C_ADDR"],
        cols=lcd_cfg["COLS"], rows=lcd_cfg["ROWS"],
    )
    DISPLAY_COLS = lcd_cfg["COLS"]
    DISPLAY_ROWS = lcd_cfg["ROWS"]


def _render(expr, cursor_pos, status="", result=None, is_menu=False,
            menu_top="", menu_bottom=""):
    display.render(expr, cursor_pos, status, result, is_menu, menu_top, menu_bottom)


# ---------------------------------------------------------------------------
# Keypad + BLE factory
# ---------------------------------------------------------------------------
if CONFIG["KEYPAD_TYPE"] == "ble_hid":
    import ubluetooth
    from ble.ble_bridge import BLEBridge
    from drivers.keypad_ble_hid import KeypadBleHid
    from ble.ble_mode_manager import BleModeManager
 
    # A single BLE radio — shared instance
    _ble = ubluetooth.BLE()
    _ble.active(True)
 
    # 1. BLEBridge FIRST: register the peripheral GATT services
    #    This must happen BEFORE any gap_connect (central).
    ble = BLEBridge(ble_instance=_ble, register_irq=False)
 
    # 2. KeypadBleHid: same instance, central mode
    keypad = KeypadBleHid(ble_instance=_ble, register_irq=False)
 
    # 3. Shared IRQ dispatcher
    #    Central events (GATTC, peripheral connect/disconnect): 7-18
    #    Peripheral events (GATTS write, advertising): 1-6
    _CENTRAL_EVENTS = frozenset(range(7, 19))
 
    def _on_ble_irq(event, data):
        if event in _CENTRAL_EVENTS:
            keypad.handle_irq(event, data)
        else:
            ble.handle_irq(event, data)
 
    _ble.irq(_on_ble_irq)
 
    # 4. Start the connection to the macropad (after GATT registration)
    keypad.start_connect()

    mode_manager = BleModeManager(ble_bridge=ble, keypad_ble=keypad)

    def _kp_status():
        return "KP:OK" if keypad.is_ready() else "KP:..."

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
    ble = BLEBridge()
    mode_manager = None

    def _kp_status():
        return ""


# ---------------------------------------------------------------------------
# BLE callback: result from the phone
# ---------------------------------------------------------------------------
_pending_result = [None]

def _on_ble_msg(msg):
    _pending_result[0] = msg

ble.callback = _on_ble_msg


# ---------------------------------------------------------------------------
# Helpers display
# ---------------------------------------------------------------------------
def _status_line(shift_mode=None):
    """Status line: shift mode for matrix, connection state for ble_hid."""
    if CONFIG["KEYPAD_TYPE"] == "matrix":
        if shift_mode == "A":   return "[SH-A]"
        if shift_mode == "B":   return "[SH-B]"
        return ""
    return _kp_status()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    input_handler = InputHandler()
    scroller      = TextScroller(DISPLAY_COLS)

    display.show_loading()
    time.sleep_ms(800)

    # Start advertising (only for the matrix keypad or ble_hid after keypad connection)
    if CONFIG["KEYPAD_TYPE"] != "ble_hid":
        ble.start_advertising(force=True)

    last_key     = None
    last_ble_adv = time.time()
    shift_mode   = None   # only for the matrix keypad

    while True:
        # -- BLE poll --
        ble.poll()

        # Matrix: restart advertising if disconnected
        if CONFIG["KEYPAD_TYPE"] == "matrix":
            if not ble.is_connected():
                now = time.time()
                if now - last_ble_adv > 5:
                    ble.start_advertising()
                    last_ble_adv = now
        else:
            # BLE HID: poll mode manager
            if mode_manager:
                mode_manager.poll()

        # -- Result from the phone --
        if _pending_result[0] is not None:
            msg = _pending_result[0]
            _pending_result[0] = None

            if msg.startswith("result:"):
                result_text = msg[7:]
                input_handler.store_local_result(result_text)
                _render(input_handler.expr, input_handler.cursor_pos,
                        status=_status_line(shift_mode),
                        result=result_text)
                time.sleep_ms(2000)
            elif msg.startswith("error:"):
                _render(input_handler.expr, input_handler.cursor_pos,
                        status="ERROR: " + msg[6:])
                time.sleep_ms(2000)

            # Return to normal/central mode
            if mode_manager:
                mode_manager.switch_to_central()
            else:
                ble.start_advertising(force=True)
            _render(input_handler.expr, input_handler.cursor_pos,
                    status=_status_line(shift_mode))
            time.sleep_ms(50)
            continue

        time.sleep_ms(20)

        # -- Read key --
        key = keypad.update()
        if key is None or key == last_key:
            last_key = key
            continue
        last_key = key

        # Shift mode (matrix only)
        if CONFIG["KEYPAD_TYPE"] == "matrix":
            if key == KeypadAction.SHIFT_A:
                shift_mode = None if shift_mode == "A" else "A"
                _render(input_handler.expr, input_handler.cursor_pos,
                        status=_status_line(shift_mode))
                continue
            if key == KeypadAction.SHIFT_B:
                shift_mode = None if shift_mode == "B" else "B"
                _render(input_handler.expr, input_handler.cursor_pos,
                        status=_status_line(shift_mode))
                continue

        # -- Process key --
        result = input_handler.process_key(key)

        # --- Ready packet: send to the phone ---
        if isinstance(result, tuple):
            expr, req_type, action, val = result

            if not expr.strip():
                _render("Expression", 0, status="empty!")
                time.sleep_ms(1000)
                _render(input_handler.expr, input_handler.cursor_pos,
                        status=_status_line(shift_mode))
                continue

            packet_str = str(result)

            if mode_manager:
                # BLE HID: switch to peripheral, then send
                mode_manager.switch_to_peripheral(result)
                _render(input_handler.expr, input_handler.cursor_pos,
                        status="Sending...")
            else:
                # Matrix: send directly over the BLE peripheral
                if ble.is_connected():
                    ble.send_result(packet_str)
                    _render(input_handler.expr, input_handler.cursor_pos,
                            status="Waiting RPi...")
                else:
                    _render(input_handler.expr, input_handler.cursor_pos,
                            status="Phone offline")
                    time.sleep_ms(1500)
                    _render(input_handler.expr, input_handler.cursor_pos,
                            status=_status_line(shift_mode))

            keypad.reset_shift()
            shift_mode = None
            continue

        # --- Menu ---
        if isinstance(result, dict):
            if result.get("menu_open"):
                keypad.reset_shift()
                shift_mode = None
                prompt_top, prompt_bottom = input_handler.get_menu_prompt()
                _render("", 0, is_menu=True,
                        menu_top=prompt_top, menu_bottom=prompt_bottom)
                continue

            if result.get("menu_choice") is not None:
                prompt_top, prompt_bottom = input_handler.get_menu_prompt()
                _render("", 0, is_menu=True,
                        menu_top=prompt_top,
                        menu_bottom="Sel:" + result["menu_choice"])
                continue

            if result.get("menu_cancelled"):
                keypad.reset_shift()
                shift_mode = None
                _render(input_handler.expr, input_handler.cursor_pos,
                        status=_status_line(shift_mode))
                continue

            if result.get("menu_error") == "empty_expression":
                _render("Expression", 0, status="empty!")
                time.sleep_ms(1000)
                _render(input_handler.expr, input_handler.cursor_pos,
                        status=_status_line(shift_mode))
                continue

            if result.get("menu_error") == "select_type":
                prompt_top, _ = input_handler.get_menu_prompt()
                _render("", 0, is_menu=True,
                        menu_top=prompt_top, menu_bottom="Choose 1-3")
                continue

        # --- Normal input: update display ---
        if result is None:
            visible = scroller.update(input_handler.expr, input_handler.cursor_pos)
            _render(visible, input_handler.cursor_pos,
                    status=_status_line(shift_mode))


if __name__ == "__main__":
    main()
