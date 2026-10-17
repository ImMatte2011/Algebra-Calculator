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
check("HISTORY_SIZE is a positive int",
      isinstance(CONFIG.get("HISTORY_SIZE"), int) and CONFIG["HISTORY_SIZE"] >= 1)
check("SHIFT_A_MAP exposes system/matrix separators",
      CONFIG["KEYPAD"]["SHIFT_A_MAP"].get("K_9") == ","
      and CONFIG["KEYPAD"]["SHIFT_A_MAP"].get("K_0") == ";")
check("SHIFT_A_MAP exposes y and SHIFT_B_MAP exposes FUNC",
      CONFIG["KEYPAD"]["SHIFT_A_MAP"].get("K_DELETE") == "y"
      and CONFIG["KEYPAD"]["SHIFT_B_MAP"].get("K_DELETE") == "CMD_FUNC")

# KEYPAD_TYPE
kt = CONFIG.get("KEYPAD_TYPE", "")
check("KEYPAD_TYPE is valid", kt in ("ble_hid", "matrix"),
      f"got '{kt}'")

# DISPLAY_TYPE
dt = CONFIG.get("DISPLAY_TYPE", "")
check("DISPLAY_TYPE is valid", dt in ("oled", "lcd", "tft", "tft_remote"),
      f"got '{dt}'")

# The UART settings are present even when this board currently uses another
# display, so a later switch to tft_remote does not silently use bad pins.
link = CONFIG.get("TFT_LINK", {})
for key in ("UART_ID", "TX_PIN", "RX_PIN", "BAUDRATE"):
    check(f"TFT_LINK.{key} present", key in link)
check("TFT_LINK pins are distinct", link.get("TX_PIN") != link.get("RX_PIN"))

# BLE_KP_MAC must be present and correctly formatted if ble_hid
if kt == "ble_hid":
    mac = CONFIG.get("BLE_KP_MAC", "")
    if mac:
        import re
        check("BLE_KP_MAC format XX:XX:XX:XX:XX:XX",
              bool(re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', mac)),
              f"got '{mac}'")
    else:
        check("BLE_KP_MAC may be unset before private settings are deployed",
              not mac)

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

# TFT section if display_type uses a TFT
if dt in ("tft", "tft_remote"):
    tft = CONFIG.get("TFT", {})
    for key in ("WIDTH", "HEIGHT", "ROTATION", "SCK_PIN", "MOSI_PIN",
                "MISO_PIN", "CS_PIN", "DC_PIN", "BL_PIN"):
        check(f"TFT.{key} present", key in tft)
    check("TFT.ROTATION valid", tft.get("ROTATION") in (0, 1, 2, 3))
    touch = CONFIG.get("TOUCH", {})
    for key in ("CS_PIN", "IRQ_PIN", "X_MIN", "X_MAX", "Y_MIN", "Y_MAX"):
        check(f"TOUCH.{key} present", key in touch)

# KEYPAD section if matrix
if kt == "matrix":
    kp = CONFIG.get("KEYPAD", {})
    for key in ("ROW_PINS", "COL_PINS", "PRIMARY_MAP"):
        check(f"KEYPAD.{key} present", key in kp)
    check("KEYPAD.ROW_PINS len == 4", len(kp.get("ROW_PINS", [])) == 4)
    check("KEYPAD.COL_PINS len == 4", len(kp.get("COL_PINS", [])) == 4)
    if dt == "oled" and CONFIG.get("OLED", {}).get("BUS") == "SPI":
        keypad_pins = set(kp.get("ROW_PINS", []) + kp.get("COL_PINS", []))
        oled = CONFIG["OLED"]
        oled_pins = {
            oled[key] for key in ("SCK_PIN", "MOSI_PIN", "DC_PIN", "CS_PIN")
            if key in oled
        }
        if oled.get("RST_PIN", -1) >= 0:
            oled_pins.add(oled["RST_PIN"])
        check("matrix keypad pins do not overlap OLED SPI pins",
              not keypad_pins.intersection(oled_pins),
              f"conflicts: {sorted(keypad_pins.intersection(oled_pins))}")

print(f"\n  {_pass} passed, {_fail} failed")
sys.exit(0 if _fail == 0 else 1)
