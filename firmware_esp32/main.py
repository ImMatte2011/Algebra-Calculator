"""
main.py — Entry point firmware ESP32 (Calc Algebraica).

Istanzia display, tastierino e BLE in base a CONFIG["DISPLAY_TYPE"] e
CONFIG["KEYPAD_TYPE"]: nessun codice hardware specifico qui, solo logica
di orchestrazione.
"""

import time
from config import CONFIG
from core.input_handler import InputHandler
from drivers.display_scroller import TextScroller
from drivers.keypad_base import KeypadAction

# ---------------------------------------------------------------------------
# Factory display
# ---------------------------------------------------------------------------
if CONFIG["DISPLAY_TYPE"] == "oled":
    from drivers.oled_display import OledDisplay
    display = OledDisplay()
    DISPLAY_COLS = CONFIG["OLED"]["WIDTH"] // 8   # 16 col con font 8px
    DISPLAY_ROWS = CONFIG["OLED"]["HEIGHT"] // 8  # 8 righe

    def _render(expr, cursor_pos, status="", result=None, is_menu=False,
                menu_top="", menu_bottom=""):
        if is_menu:
            display._fb.fill(0)
            display._fb.text("Tipo/Azione:", 0, 0, 1)
            display._fb.text(menu_top,    0, 16, 1)
            display._fb.text(menu_bottom, 0, 24, 1)
            display._fb.text("CLR=annulla", 0, 56, 1)
            display.show()
        elif result is not None:
            display._fb.fill(0)
            display._fb.text("Risultato:", 0, 0, 1)
            display.show_text_large(result[:8], y=12)
            display._fb.text(result[8:], 0, 28, 1)
            display._fb.text(status, 0, 56, 1)
            display.show()
        else:
            display.show_expr_and_status(expr, status)

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
        if is_menu:
            display.show_text(menu_top,    0)
            display.show_text(menu_bottom, 1)
        elif result is not None:
            display.show_text("Risultato:", 0)
            display.show_text(result[:DISPLAY_COLS], 1)
        else:
            display.show_text(expr[:DISPLAY_COLS], 0)
            display.show_text(status[:DISPLAY_COLS], 1)


# ---------------------------------------------------------------------------
# Factory tastierino + BLE
# ---------------------------------------------------------------------------
if CONFIG["KEYPAD_TYPE"] == "ble_hid":
    import ubluetooth
    from drivers.keypad_ble_hid import KeypadBleHid
    from ble.ble_bridge import BLEBridge
    from ble.ble_mode_manager import BleModeManager

    # Istanza BLE condivisa tra tastierino (central) e bridge (peripheral)
    _ble_instance = ubluetooth.BLE()
    _ble_instance.active(True)

    keypad = KeypadBleHid(ble_instance=_ble_instance)
    ble    = BLEBridge(ble_instance=_ble_instance)
    mode_manager = BleModeManager(ble_bridge=ble, keypad_ble=keypad)

    def _kp_status():
        if keypad.is_ready():
            return "KP:OK"
        return "KP:conn..."

else:
    # Matrix keypad: BLE sempre in peripheral
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
# Callback BLE: risultato dal telefono
# ---------------------------------------------------------------------------
_pending_result = [None]

def _on_ble_msg(msg):
    _pending_result[0] = msg

ble.callback = _on_ble_msg


# ---------------------------------------------------------------------------
# Helpers display
# ---------------------------------------------------------------------------
def _status_line(shift_mode=None):
    """Status in fondo: shift mode per matrix, connessione per ble_hid."""
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

    # Avvio advertising (solo se matrix keypad o ble_hid dopo connessione kp)
    if CONFIG["KEYPAD_TYPE"] != "ble_hid":
        ble.start_advertising(force=True)

    last_key     = None
    last_ble_adv = time.time()
    shift_mode   = None   # solo per matrix keypad

    while True:
        # -- BLE poll --
        ble.poll()

        # Matrix: restart advertising se disconnesso
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

        # -- Risultato dal telefono --
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
                        status="ERRORE: " + msg[6:])
                time.sleep_ms(2000)

            # Torna in modalità normal/central
            if mode_manager:
                mode_manager.switch_to_central()
            else:
                ble.start_advertising(force=True)
            _render(input_handler.expr, input_handler.cursor_pos,
                    status=_status_line(shift_mode))
            time.sleep_ms(50)
            continue

        time.sleep_ms(20)

        # -- Leggi tasto --
        key = keypad.update()
        if key is None or key == last_key:
            last_key = key
            continue
        last_key = key

        # Shift mode (solo matrix)
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

        # -- Processa tasto --
        result = input_handler.process_key(key)

        # --- Pacchetto pronto: invia al telefono ---
        if isinstance(result, tuple):
            expr, req_type, action, val = result

            if not expr.strip():
                _render("Espressione", 0, status="vuota!")
                time.sleep_ms(1000)
                _render(input_handler.expr, input_handler.cursor_pos,
                        status=_status_line(shift_mode))
                continue

            packet_str = str(result)

            if mode_manager:
                # BLE HID: switch in peripheral, poi invia
                mode_manager.switch_to_peripheral(result)
                _render(input_handler.expr, input_handler.cursor_pos,
                        status="Invio...")
            else:
                # Matrix: invia direttamente sul BLE peripheral
                if ble.is_connected():
                    ble.send_result(packet_str)
                    _render(input_handler.expr, input_handler.cursor_pos,
                            status="Attesa RPi...")
                else:
                    _render(input_handler.expr, input_handler.cursor_pos,
                            status="Tel non connesso")
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
                _render("Espressione", 0, status="vuota!")
                time.sleep_ms(1000)
                _render(input_handler.expr, input_handler.cursor_pos,
                        status=_status_line(shift_mode))
                continue

            if result.get("menu_error") == "select_type":
                prompt_top, _ = input_handler.get_menu_prompt()
                _render("", 0, is_menu=True,
                        menu_top=prompt_top, menu_bottom="Scegli 1-3")
                continue

        # --- Input normale: aggiorna display ---
        if result is None:
            visible = scroller.update(input_handler.expr, input_handler.cursor_pos)
            _render(visible, input_handler.cursor_pos,
                    status=_status_line(shift_mode))


if __name__ == "__main__":
    main()