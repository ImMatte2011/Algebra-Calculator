"""
test_input_handler.py — Tests InputHandler without hardware.
Works on both ESP32 and PC.

Usage:
    mpremote run firmware_esp32/tests/test_input_handler.py
    or:  python firmware_esp32/tests/test_input_handler.py
"""
import sys, os
if sys.implementation.name == "micropython":
    sys.path.insert(0, "/")
else:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

# KeypadBase depends on ubluetooth only in the BLE driver, not in the base.
# On PC, ubluetooth does not exist: a minimal mock is used to import the modules.
try:
    import ubluetooth
except ImportError:
    import types
    ubluetooth = types.ModuleType("ubluetooth")
    ubluetooth.BLE  = object
    ubluetooth.UUID = lambda x: x
    sys.modules["ubluetooth"] = ubluetooth

try:
    import machine
except ImportError:
    import types
    machine = types.ModuleType("machine")
    machine.Pin  = object
    machine.I2C  = object
    machine.SPI  = object
    sys.modules["machine"] = machine

try:
    from drivers.keypad_base import KeypadAction
    from core.input_handler import InputHandler
except Exception as e:
    print("FAIL import:", e)
    import traceback; traceback.print_exc()
    sys.exit(1)

_pass = 0
_fail = 0

def check(name, condition, detail=""):
    global _pass, _fail
    if condition:
        print(f"  PASS  {name}")
        _pass += 1
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        _fail += 1

def fresh():
    return InputHandler()

print("\n=== test_input_handler ===")

# --- Character insertion ---
ih = fresh()
ih.process_key("x")
ih.process_key("^")
ih.process_key("2")
check("character insertion", ih.expr == "x^2", f"got '{ih.expr}'")

# --- Cursor ---
ih = fresh()
for c in "abc":
    ih.process_key(c)
ih.process_key(KeypadAction.LEFT)
check("LEFT moves the cursor", ih.cursor_pos == 2, f"pos={ih.cursor_pos}")
ih.process_key(KeypadAction.RIGHT)
check("RIGHT moves the cursor", ih.cursor_pos == 3)

# --- BACKSPACE ---
ih = fresh()
for c in "xyz":
    ih.process_key(c)
ih.process_key(KeypadAction.BACKSPACE)
check("BACKSPACE removes the character before the cursor",
      ih.expr == "xy", f"got '{ih.expr}'")

# --- DELETE ---
ih = fresh()
for c in "xyz":
    ih.process_key(c)
ih.process_key(KeypadAction.LEFT)
ih.process_key(KeypadAction.LEFT)
ih.process_key(KeypadAction.DELETE)
check("DELETE removes the character after the cursor",
      ih.expr == "xz", f"got '{ih.expr}'")

# --- CLEAR ---
ih = fresh()
for c in "x^2-1":
    ih.process_key(c)
ih.process_key(KeypadAction.CLEAR)
check("CLEAR clears the expression", ih.expr == "")
check("CLEAR resets the cursor", ih.cursor_pos == 0)

# --- SQRT ---
ih = fresh()
ih.process_key("2")
result = ih.process_key(KeypadAction.SQRT)
check("SQRT inserts 'sqrt('", ih.expr == "2sqrt(",
      f"got '{ih.expr}'")
check("SQRT returns None (normal editing)", result is None)
check("cursor advances by 5 after SQRT",
      ih.cursor_pos == 6, f"pos={ih.cursor_pos}")

# --- Direct Layer 3 actions ---
ih = fresh()
for c in "x^2":
    ih.process_key(c)
result = ih.process_key(KeypadAction.ACTION_SIMPLIFY)
check("ACTION_SIMPLIFY returns a tuple", isinstance(result, tuple))
check("ACTION_SIMPLIFY: type expression",
      result[1] == "expression", f"got '{result[1]}'")
check("ACTION_SIMPLIFY: action simplify",
      result[2] == "simplify", f"got '{result[2]}'")
check("ACTION_SIMPLIFY: expression is correct",
      result[0] == "x^2", f"got '{result[0]}'")

ih = fresh()
for c in "x+1=0":
    ih.process_key(c)
result = ih.process_key(KeypadAction.TYPE_EQUATION)
check("TYPE_EQUATION returns a tuple", isinstance(result, tuple))
check("TYPE_EQUATION: type equation",
      result[1] == "equation", f"got '{result[1]}'")
check("TYPE_EQUATION: action None",
      result[2] is None, f"got '{result[2]}'")

ih = fresh()
for c in "x>0":
    ih.process_key(c)
result = ih.process_key(KeypadAction.TYPE_INEQUALITY)
check("TYPE_INEQUALITY: type inequality",
      result[1] == "inequality")

# --- Empty expression with direct action ---
ih = fresh()
result = ih.process_key(KeypadAction.ACTION_FACTOR)
check("action on empty expression → menu_error",
      isinstance(result, dict) and result.get("menu_error") == "empty_expression",
      f"got {result}")

# --- TYPE_EXPRESSION opens the action sub-menu ---
ih = fresh()
for c in "x^2":
    ih.process_key(c)
result = ih.process_key(KeypadAction.TYPE_EXPRESSION)
check("TYPE_EXPRESSION opens a menu",
      isinstance(result, dict) and result.get("menu_open"),
      f"got {result}")
check("menu_stage is expression_action",
      ih.menu_stage == "expression_action")

# --- Interactive menu (classic ENTER) ---
ih = fresh()
for c in "x^2-1":
    ih.process_key(c)
result = ih.process_key(KeypadAction.ENTER)
check("ENTER opens the type menu", isinstance(result, dict) and result.get("menu_open"))
check("waiting_menu True", ih.waiting_menu)

ih.process_key("2")   # choose "equation"
result = ih.process_key(KeypadAction.ENTER)
check("ENTER with equation type returns a tuple", isinstance(result, tuple))
check("equation type", result[1] == "equation")

# --- CLEAR cancels the menu ---
ih = fresh()
for c in "abc":
    ih.process_key(c)
ih.process_key(KeypadAction.ENTER)
result = ih.process_key(KeypadAction.CLEAR)
check("CLEAR in menu clears and returns menu_cancelled",
      isinstance(result, dict) and result.get("menu_cancelled"))
check("waiting_menu False after CLEAR", not ih.waiting_menu)

# --- reset() ---
ih = fresh()
for c in "hello":
    ih.process_key(c)
ih.reset()
check("reset clears expr", ih.expr == "")
check("reset closes the menu", not ih.waiting_menu)

print(f"\n  {_pass} passed, {_fail} failed")
sys.exit(0 if _fail == 0 else 1)
