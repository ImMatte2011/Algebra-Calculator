"""
test_config.py — Validates the structure of config.py without hardware.
Works on both ESP32 and PC (no hardware dependencies).

Usage:
    mpremote run firmware_esp32/tests/test_config.py
    or:  python firmware_esp32/tests/test_config.py
"""
import sys, os
if sys.implementation.name == "micropython":
    sys.path.insert(0, "/")
else:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import CONFIG
except Exception as e:
    print("FAIL import config:", e)
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

print("\n=== test_config ===")

# Required top-level keys
for key in ("KEYPAD_TYPE", "DISPLAY_TYPE",
            "BLE_NAME", "BLE_SERVICE_UUID",
            "BLE_EXPR_CHAR_UUID", "BLE_RESULT_CHAR_UUID"):
    check(f"CONFIG has '{key}'", key in CONFIG)

# KEYPAD_TYPE
kt = CONFIG.get("KEYPAD_TYPE", "")
check("KEYPAD_TYPE is valid", kt in ("ble_hid", "matrix"),
      f"got '{kt}'")

# DISPLAY_TYPE
dt = CONFIG.get("DISPLAY_TYPE", "")
check("DISPLAY_TYPE is valid", dt in ("oled", "lcd"),
      f"got '{dt}'")

# BLE_KP_MAC must be present and correctly formatted if ble_hid
if kt == "ble_hid":
    mac = CONFIG.get("BLE_KP_MAC", "")
    import re
    check("BLE_KP_MAC format XX:XX:XX:XX:XX:XX",
          bool(re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', mac)),
          f"got '{mac}'")

# OLED section if display_type == oled
if dt == "oled":
    oled = CONFIG.get("OLED", {})
    for key in ("BUS", "CONTROLLER", "WIDTH", "HEIGHT"):
        check(f"OLED.{key} present", key in oled)
    check("OLED.BUS valid", oled.get("BUS") in ("SPI", "I2C"))
    check("OLED.CONTROLLER valid",
          oled.get("CONTROLLER") in ("SSD1306", "SSD1309", "SH1106"))
    if oled.get("BUS") == "SPI":
        for pin in ("SCK_PIN", "MOSI_PIN", "DC_PIN", "CS_PIN"):
            check(f"OLED SPI pin {pin} present", pin in oled)
    else:
        for pin in ("SCL_PIN", "SDA_PIN", "I2C_ADDR"):
            check(f"OLED I2C param {pin} present", pin in oled)
    check("OLED.USE_GLYPHS is bool",
          isinstance(oled.get("USE_GLYPHS", True), bool))

# LCD section if display_type == lcd
if dt == "lcd":
    lcd = CONFIG.get("LCD", {})
    for key in ("SCL_PIN", "SDA_PIN", "I2C_ADDR", "COLS", "ROWS"):
        check(f"LCD.{key} present", key in lcd)

# KEYPAD section if matrix
if kt == "matrix":
    kp = CONFIG.get("KEYPAD", {})
    for key in ("ROW_PINS", "COL_PINS", "PRIMARY_MAP"):
        check(f"KEYPAD.{key} present", key in kp)
    check("KEYPAD.ROW_PINS len == 4", len(kp.get("ROW_PINS", [])) == 4)
    check("KEYPAD.COL_PINS len == 4", len(kp.get("COL_PINS", [])) == 4)

print(f"\n  {_pass} passed, {_fail} failed")
sys.exit(0 if _fail == 0 else 1)
