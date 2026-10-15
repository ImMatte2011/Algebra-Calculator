"""
main.py — Application entry point. Pure orchestration logic; no hardware specifics.

CalculatorApp receives all peripherals via constructor injection and drives
the expression-editing → BLE-send → result-display cycle.
"""

import time
import sys
import machine
from config import CONFIG
from core.input_handler import InputHandler
from drivers.display_scroller import TextScroller
from drivers.keypad_base import KeypadAction
from hardware_setup import get_hardware


class CalculatorApp:

    def __init__(self, display, keypad, ble, mode_manager, wdt):
        self.display      = display
        self.keypad       = keypad
        self.ble          = ble          # BLEBridge or None (ble_hid lazy)
        self.mode_manager = mode_manager # BleModeManager or None
        self.wdt          = wdt

        self.input_handler = InputHandler()
        self.scroller      = TextScroller(display.cols)

        # Result slot written by the BLE callback (IRQ context).
        self._pending_result = [None]

        # Input-loop state.
        self._last_countdown = -1

        # Keep the startup prompt visible until the first keypress.
        self._kp_was_ready   = False
        self._awaiting_input = False
        self._first_input    = False

        if self.ble is not None:
            self.ble.callback = self._on_ble_msg

    # -----------------------------------------------------------------------
    # BLE message callback (called from IRQ / poll context)
    # -----------------------------------------------------------------------
    def _on_ble_msg(self, msg):
        self._pending_result[0] = msg

    # -----------------------------------------------------------------------
    # Display helpers
    # -----------------------------------------------------------------------
    def _render(self, expr, cursor_pos, status="", result=None,
                is_menu=False, menu_top="", menu_bottom=""):
        self.display.render(expr, cursor_pos, status, result,
                            is_menu, menu_top, menu_bottom)

    def _status_line(self):
        if CONFIG["KEYPAD_TYPE"] == "matrix":
            if getattr(self.keypad, "shift_mode", None) == "A": return "[SH-A]"
            if getattr(self.keypad, "shift_mode", None) == "B": return "[SH-B]"
            return ""
        return "KP:OK" if self.keypad.is_ready() else "KP:..."

    def _show_waiting_prompt(self):
        rows = getattr(self.display, "rows", 2)
        if rows <= 0:
            return
        first_row = max(0, (rows - 2) // 2)
        self.display.show_text("Ready for input", first_row)
        if first_row + 1 < rows:
            self.display.show_text("Enter expression", first_row + 1)

    # -----------------------------------------------------------------------
    # run(): initial UI setup + main loop
    # -----------------------------------------------------------------------
    def run(self):
        self.display.show_loading()
        time.sleep_ms(800)
        if self.wdt: self.wdt.feed()

        if CONFIG["KEYPAD_TYPE"] != "ble_hid":
            if hasattr(self.ble, 'start_advertising'):
                self.ble.start_advertising(force=True)
        if CONFIG["KEYPAD_TYPE"] == "matrix":
            self._kp_was_ready   = True
            self._awaiting_input = True
            self.display.clear()
            self._show_waiting_prompt()

        self._run_sync()

    def _run_sync(self):
        while True:
            if self.wdt: self.wdt.feed()
            self._poll_network()
            if self._handle_pending_result():
                continue
            time.sleep_ms(20)
            self._handle_input()

    # -----------------------------------------------------------------------
    # _poll_network(): BLE polling, re-advertising, countdown display
    # -----------------------------------------------------------------------
    def _poll_network(self):
        if self.ble is not None:
            self.ble.poll()

        if CONFIG["KEYPAD_TYPE"] == "matrix":
            if self.ble.needs_advertise:
                self.ble.start_advertising()
        else:
            if not self._kp_was_ready and self.keypad.is_ready():
                self._kp_was_ready   = True
                self._awaiting_input = True
                self.display.clear()
                self._show_waiting_prompt()

            if self.mode_manager is not None:
                poll_info = self.mode_manager.poll()
                if isinstance(poll_info, dict):
                    if poll_info.get("timeout"):
                        self._render(self.input_handler.expr,
                                    self.input_handler.cursor_pos,
                                    status="Phone timeout")
                        time.sleep_ms(2000)
                        if self.wdt: self.wdt.feed()
                        self._last_countdown = -1
                        self._render(self.input_handler.expr,
                                    self.input_handler.cursor_pos,
                                    status=self._status_line())
                    elif "countdown" in poll_info:
                        cd = poll_info["countdown"]
                        if cd != self._last_countdown:
                            self._last_countdown = cd
                            self._render(self.input_handler.expr,
                                        self.input_handler.cursor_pos,
                                        status="App...{}s".format(cd))

    # -----------------------------------------------------------------------
    # _handle_pending_result(): process a reply from the phone
    # Returns True so the caller can `continue` the main loop immediately.
    # -----------------------------------------------------------------------
    def _handle_pending_result(self):
        if self._pending_result[0] is None:
            return False

        msg = self._pending_result[0]
        self._pending_result[0] = None
        self._last_countdown = -1

        if msg.startswith("res:"):
            msg = msg[4:]

        if msg.startswith("result:"):
            result_text = msg[7:]
            self.input_handler.store_local_result(result_text)
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status=self._status_line(), result=result_text)
            time.sleep_ms(2000)
            if self.wdt: self.wdt.feed()
        elif msg.startswith("err:") or msg.startswith("error:"):
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status="ERROR: " + msg.split(":", 1)[1])
            time.sleep_ms(2000)
            if self.wdt: self.wdt.feed()
        else:
            # Display unrecognized message formats as raw results.
            self.input_handler.store_local_result(msg)
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status=self._status_line(), result=msg)
            time.sleep_ms(2000)
            if self.wdt: self.wdt.feed()

        # Resume the appropriate BLE role.
        if self.mode_manager is not None:
            self.mode_manager.switch_to_central()
        else:
            self.ble.start_advertising(force=True)

        self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                     status=self._status_line())
        time.sleep_ms(50)
        return True

    # -----------------------------------------------------------------------
    # _handle_input(): read one keypress and dispatch to the right handler
    # -----------------------------------------------------------------------
    def _handle_input(self):
        key = self.keypad.update()
        if key is None:
            return

        # Shift-layer toggles (matrix mode only).
        if CONFIG["KEYPAD_TYPE"] == "matrix" and key in (
                KeypadAction.SHIFT_A, KeypadAction.SHIFT_B):
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status=self._status_line())
            return

        result = self.input_handler.process_key(key)

        if isinstance(result, tuple):
            self._handle_send(result)
        elif isinstance(result, dict):
            self._handle_menu(result)
        else:
            self._update_display(key)

    # -----------------------------------------------------------------------
    # _handle_send(): validate and transmit an expression packet to the phone
    # -----------------------------------------------------------------------
    def _handle_send(self, result):
        expr, req_type, action, val = result

        if not expr.strip():
            self._render("Expression", 0, status="empty!")
            time.sleep_ms(1000)
            if self.wdt: self.wdt.feed()
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                        status=self._status_line())
            self.keypad.reset_shift()
            return

        if CONFIG["KEYPAD_TYPE"] == "ble_hid" and self.mode_manager is not None:
            self._last_countdown = CONFIG.get("BLE_PHONE_TIMEOUT_S", 30)
            self.mode_manager.switch_to_peripheral(result)
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                        status="App...{}s".format(self._last_countdown))

        else:
            if self.ble.is_connected():
                self.ble.send_result(str(result))
                self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                            status="Waiting RPi...")
            else:
                self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                            status="Phone offline")
                time.sleep_ms(1500)
                if self.wdt: self.wdt.feed()
                self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                            status=self._status_line())

        self.keypad.reset_shift()

    # -----------------------------------------------------------------------
    # _handle_menu(): route a menu result dict to the correct display update
    # -----------------------------------------------------------------------
    def _handle_menu(self, result):
        if result.get("input_error") == "expression_too_long":
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status="Expression too long")

        elif result.get("menu_open"):
            self.keypad.reset_shift()
            pt, pb = self.input_handler.get_menu_prompt()
            self._render("", 0, is_menu=True, menu_top=pt, menu_bottom=pb)

        elif result.get("menu_choice") is not None:
            pt, pb = self.input_handler.get_menu_prompt()
            self._render("", 0, is_menu=True, menu_top=pt,
                         menu_bottom="Sel:" + result["menu_choice"])

        elif result.get("menu_cancelled"):
            self.keypad.reset_shift()
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status=self._status_line())

        elif result.get("menu_error") == "empty_expression":
            self._render("Expression", 0, status="empty!")
            time.sleep_ms(1000)
            if self.wdt: self.wdt.feed()
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status=self._status_line())

        elif result.get("menu_error") == "select_type":
            pt, _ = self.input_handler.get_menu_prompt()
            self._render("", 0, is_menu=True, menu_top=pt, menu_bottom="Choose 1-3")

    # -----------------------------------------------------------------------
    # _update_display(): refresh expression line after a normal keypress
    # -----------------------------------------------------------------------
    def _update_display(self, key):
        # First character typed clears the waiting prompt.
        if self._awaiting_input and not self._first_input and isinstance(key, str):
            self._first_input    = True
            self._awaiting_input = False

        if not self._awaiting_input:
            expression = self.input_handler.expr
            cursor_pos = self.input_handler.cursor_pos
            if CONFIG["DISPLAY_TYPE"] == "oled":
                visible = expression
            else:
                visible = self.scroller.update(expression, cursor_pos)
                cursor_pos = max(0, min(
                    cursor_pos - self.scroller.window_start,
                    len(visible),
                ))
            self._render(visible, cursor_pos, status=self._status_line())


if __name__ == "__main__":
    hw_display, hw_keypad, hw_ble, hw_mode_manager, hw_wdt = get_hardware()
    app = CalculatorApp(hw_display, hw_keypad, hw_ble, hw_mode_manager, hw_wdt)
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[INFO] User interrupt detected.")
        hw_ble.ble.active(False)
    except Exception as e:
        print("\n[ERROR] Unhandled firmware exception; restarting.")
        sys.print_exception(e)
        machine.reset()