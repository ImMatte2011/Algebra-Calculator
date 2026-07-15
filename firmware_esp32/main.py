"""
main.py — Application entry point. Pure orchestration logic; no hardware specifics.

CalculatorApp receives all peripherals via constructor injection and drives
the expression-editing → BLE-send → result-display cycle.
"""

import time
import sys
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
        self.last_key        = None
        self.shift_mode      = None
        self._last_ble_adv   = 0
        self._last_countdown = -1

        # Waiting-prompt state: show "In attesa di input..." until first keypress.
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
            if self.shift_mode == "A": return "[SH-A]"
            if self.shift_mode == "B": return "[SH-B]"
            return ""
        return "KP:OK" if self.keypad.is_ready() else "KP:..."

    # -----------------------------------------------------------------------
    # run(): initial UI setup + main loop
    # -----------------------------------------------------------------------
    def run(self):
        self.display.show_loading()
        time.sleep_ms(800)
        if self.wdt: self.wdt.feed()

        if CONFIG["KEYPAD_TYPE"] != "ble_hid":
            self.ble.start_advertising(force=True)

        self._last_ble_adv = time.time()

        # Matrix keypad is always ready; show the waiting prompt immediately.
        if CONFIG["KEYPAD_TYPE"] == "matrix":
            self._kp_was_ready   = True
            self._awaiting_input = True
            self.display.clear()
            self.display.show_text("In attesa di", 3)
            self.display.show_text("  input...", 4)

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
            if not self.ble.is_connected():
                now = time.time()
                if now - self._last_ble_adv > 5:
                    self.ble.start_advertising()
                    self._last_ble_adv = now

        else:
            # Detect the first macropad connection and show the waiting prompt.
            if not self._kp_was_ready and self.keypad.is_ready():
                self._kp_was_ready   = True
                self._awaiting_input = True
                self.display.clear()
                self.display.show_text("In attesa di", 3)
                self.display.show_text("  input...", 4)

            if self.mode_manager is not None:
                poll_info = self.mode_manager.poll()
                if isinstance(poll_info, dict):
                    if poll_info.get("timeout"):
                        # Timeout expired: notify user then return to idle.
                        self._render(self.input_handler.expr,
                                     self.input_handler.cursor_pos,
                                     status="Timeout:no phone")
                        time.sleep_ms(2000)
                        if self.wdt: self.wdt.feed()
                        self._last_countdown = -1
                        self._render(self.input_handler.expr,
                                     self.input_handler.cursor_pos,
                                     status=self._status_line())
                    elif "countdown" in poll_info:
                        cd = poll_info["countdown"]
                        if cd != self._last_countdown:   # redraw only on second change
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

        if msg.startswith("result:"):
            result_text = msg[7:]
            self.input_handler.store_local_result(result_text)
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status=self._status_line(), result=result_text)
            time.sleep_ms(2000)
            if self.wdt: self.wdt.feed()
        elif msg.startswith("error:"):
            self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                         status="ERROR: " + msg[6:])
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
        if key is None or key == self.last_key:
            self.last_key = key
            return

        self.last_key = key

        # Shift-layer toggles (matrix mode only).
        if CONFIG["KEYPAD_TYPE"] == "matrix":
            if key == KeypadAction.SHIFT_A:
                self.shift_mode = None if self.shift_mode == "A" else "A"
                self._render(self.input_handler.expr, self.input_handler.cursor_pos,
                             status=self._status_line())
                return
            if key == KeypadAction.SHIFT_B:
                self.shift_mode = None if self.shift_mode == "B" else "B"
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
            self.shift_mode = None
            return

        if CONFIG["KEYPAD_TYPE"] == "ble_hid":
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
        self.shift_mode = None

    # -----------------------------------------------------------------------
    # _handle_menu(): route a menu result dict to the correct display update
    # -----------------------------------------------------------------------
    def _handle_menu(self, result):
        if result.get("menu_open"):
            self.keypad.reset_shift()
            self.shift_mode = None
            pt, pb = self.input_handler.get_menu_prompt()
            self._render("", 0, is_menu=True, menu_top=pt, menu_bottom=pb)

        elif result.get("menu_choice") is not None:
            pt, pb = self.input_handler.get_menu_prompt()
            self._render("", 0, is_menu=True, menu_top=pt,
                         menu_bottom="Sel:" + result["menu_choice"])

        elif result.get("menu_cancelled"):
            self.keypad.reset_shift()
            self.shift_mode = None
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
            visible = self.scroller.update(self.input_handler.expr,
                                           self.input_handler.cursor_pos)
            self._render(visible, self.input_handler.cursor_pos,
                         status=self._status_line())


if __name__ == "__main__":
    hw_display, hw_keypad, hw_ble, hw_mode_manager, hw_wdt = get_hardware()
    app = CalculatorApp(hw_display, hw_keypad, hw_ble, hw_mode_manager, hw_wdt)
    try:
        app.run()
    except KeyboardInterrupt:
            print("\n[WAKE] User interrupt detected.")

    except Exception as e:
        print("\n[ERROR]")
        sys.print_exception(e)
        time.sleep_ms(2000)

    finally:
        if hw_ble is not None:
            print("[CLEANUP] Forced NimBLE stack deactivation...")
            try:
                import ubluetooth
                ubluetooth.BLE().active(False)

                import time
                time.sleep_ms(300)
 
                print("[CLEANUP] Stack powered off. Safe REPL.")
            except:
                pass