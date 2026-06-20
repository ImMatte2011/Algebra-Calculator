import time
from config import CONFIG
from drivers.lcd_display import LCDDisplay
from drivers.keypad_abstract import KeypadAbstract, KeypadAction
from drivers.display_scroller import TextScroller
from core.input_handler import InputHandler
from ble.ble_bridge import BLEBridge

def pad_right(text: str, width: int) -> str:
    if len(text) >= width:
        return text[:width]
    return text + " " * (width - len(text))

def render_status_line(text: str = "", shift_mode=None, cols: int = 16) -> str:
    if shift_mode == "A":
        indicator = "[SH-A]"
    elif shift_mode == "B":
        indicator = "[SH-B]"
    else:
        indicator = ""
    available = cols - len(indicator)
    base_text = text[:available]
    return base_text + " " * (available - len(base_text)) + indicator

def main():
    lcd_config = CONFIG["LCD"]
    keypad_config = CONFIG["KEYPAD"]

    display = LCDDisplay(
        scl_pin=lcd_config["SCL_PIN"],
        sda_pin=lcd_config["SDA_PIN"],
        i2c_addr=lcd_config["I2C_ADDR"],
        cols=lcd_config["COLS"],
        rows=lcd_config["ROWS"],
    )

    keypad = KeypadAbstract(
        row_pins=keypad_config["ROW_PINS"],
        col_pins=keypad_config["COL_PINS"],
        primary_map=keypad_config["PRIMARY_MAP"],
        shift_a_map=keypad_config.get("SHIFT_A_MAP"),
        shift_b_map=keypad_config.get("SHIFT_B_MAP"),
    )

    input_handler = InputHandler()
    scroller = TextScroller(lcd_config["COLS"])

    # --- INTEGRAZIONE BLE ---
    def on_ble_msg(msg):
        if msg.startswith("res:"):
            display.show_text("RISULTATO:", 0)
            display.show_text(pad_right(msg[4:], lcd_config["COLS"]), 1)
        elif msg.startswith("err:"):
            display.show_text("ERRORE:", 0)
            display.show_text(pad_right(msg[4:], lcd_config["COLS"]), 1)
        else:
            display.show_text("Msg:", 0)
            display.show_text(pad_right(msg, lcd_config["COLS"]), 1)

    ble = BLEBridge(callback_on_receive=on_ble_msg)
    # -------------------------

    display.clear()
    display.lcd.blink_cursor_on()
    display.show_text(scroller.update(input_handler.expr, input_handler.cursor_pos), 0)
    display.show_text(render_status_line("", keypad.shift_mode, lcd_config["COLS"]), 1)
    display.lcd.move_to(scroller.cursor_pos, 0)

    ultimo_tasto = None

    ble.start_advertising(force=True)
    last_ble_check = time.time()

    while True:
        ble.poll()

        if ble.check_connection() is None:
            now = time.time()
            if now - last_ble_check > 5:
                ble.start_advertising()
                last_ble_check = now
        else:
            last_ble_check = time.time()

        # Breve pausa per stabilità CPU
        time.sleep_ms(50)

        key = keypad.update()
        if key is None or key == ultimo_tasto:
            ultimo_tasto = key
            continue

        ultimo_tasto = key
        result = input_handler.process_key(key)

        # 1. Gestione Invio Pacchetto al RPi
        if isinstance(result, tuple):
            packet_str = str(result)
            ble.send_result(packet_str)
            display.show_text("Invio a RPi...", 0)
            display.show_text(" " * lcd_config["COLS"], 1)
            input_handler.reset()
            keypad.reset_shift()
            display.show_text("Ready", 0)
            display.show_text(render_status_line("", keypad.shift_mode, lcd_config["COLS"]), 1)
            continue

        # 2. Gestione Menù
        if isinstance(result, dict):
            if result.get("menu_open"):
                keypad.reset_shift()
                display.lcd.hide_cursor()
                prompt_top, prompt_bottom = input_handler.get_menu_prompt()
                display.show_text(prompt_top, 0)
                display.show_text(prompt_bottom, 1)
                continue

            if result.get("menu_choice") is not None:
                prompt_top, _ = input_handler.get_menu_prompt()
                display.lcd.hide_cursor()
                display.show_text(prompt_top, 0)
                display.show_text(pad_right("Sel:" + result["menu_choice"], lcd_config["COLS"]), 1)
                continue

            if result.get("menu_cancelled"):
                keypad.reset_shift()
                visible_text = scroller.update(input_handler.expr, input_handler.cursor_pos)
                display.show_text(visible_text, 0)
                display.show_text(render_status_line("", keypad.shift_mode, lcd_config["COLS"]), 1)
                display.lcd.blink_cursor_on()
                display.lcd.move_to(scroller.cursor_pos, 0)
                continue

            if result.get("menu_error") == "select_type":
                display.lcd.hide_cursor()
                prompt_top, _ = input_handler.get_menu_prompt()
                display.show_text(prompt_top, 0)
                display.show_text(pad_right("Choose 1-3", lcd_config["COLS"]), 1)
                continue

        # 3. Input Normale
        if result is None:
            if input_handler.waiting_menu:
                display.lcd.hide_cursor()
                prompt_top, prompt_bottom = input_handler.get_menu_prompt()
                display.show_text(prompt_top, 0)
                display.show_text(prompt_bottom, 1)
            else:
                visible_text = scroller.update(input_handler.expr, input_handler.cursor_pos)
                display.show_text(visible_text, 0)
                display.show_text(render_status_line("", keypad.shift_mode, lcd_config["COLS"]), 1)
                display.lcd.blink_cursor_on()
                display.lcd.move_to(scroller.cursor_pos, 0)

if __name__ == "__main__":
    main()