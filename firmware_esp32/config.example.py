"""
config.py — Hardware configuration for the ESP32 firmware.

To change the hardware variant, edit only this file.
The rest of the firmware (main.py, drivers, etc.) should not be touched.

KEYPAD_TYPE:  "ble_hid"  → BLE HID macropad
              "matrix"   → 4x4 matrix keypad via GPIO
DISPLAY_TYPE: "oled"     → OLED display SSD1309/SSD1306/SH1106
              "lcd"      → 16x2 I2C LCD display
"""

CONFIG = {
    # ------------------------------------------------------------------
    # Selected hardware (change only these two to switch variants)
    # ------------------------------------------------------------------
    "KEYPAD_TYPE":  "matrix",   # "matrix" | "ble_hid"
    "DISPLAY_TYPE": "oled",     # "oled"   | "lcd"

    # ------------------------------------------------------------------
    # Watchdog timer (enabled by default, can be disabled for debugging)
    # ------------------------------------------------------------------
    "ENABLE_WATCHDOG":     True,
    "WATCHDOG_TIMEOUT_MS": 60000,

    # ------------------------------------------------------------------
    # Communication mode
    # ------------------------------------------------------------------
    "COMMUNICATION_MODE": "ble",   # "ble" | "wifi"

    # WiFi settings (used when COMMUNICATION_MODE="wifi")
    "WIFI": {
        "SOLVE_MODE":       "auto",                       # "direct" | "phone" | "auto"
        "SSID":             "YourSSID",
        "PASSWORD":         "YourPassword",
        "RPI_URL":          "http://192.168.1.100:8000",  # host:port per direct
        "API_TOKEN":        "",                           # Bearer token; empty = skip header
        "API_PATH":         "/solve",
        "PHONE_URL":        "http://192.168.43.1:8765",   # smartphone IP on Android hotspot
        "PHONE_TOKEN":      "esp32-secret",               # same value in app settings
        "PHONE_PATH":       "/solve",
        "TIMEOUT_S":        10,
        "PING_TIMEOUT_S":   4,                            # timeout TCP for auto-detecting
        "RETRY_INTERVAL_S": 10,
        "RECHECK_S":        60,                           # auto: ogni quanto ritestare direct dopo fallback
    },

    # ------------------------------------------------------------------
    # BLE toward the phone (peripheral — used when COMMUNICATION_MODE="ble")
    # ------------------------------------------------------------------
    "BLE_NAME":             "CALC-ESP32",
    "BLE_SERVICE_UUID":     "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "BLE_EXPR_CHAR_UUID":   "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "BLE_RESULT_CHAR_UUID": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "PHONE_MAC":            "XX:XX:XX:XX:XX:XX",
    "BLE_PHONE_TIMEOUT_S":  30,

    # ------------------------------------------------------------------
    # BLE HID macropad (central — used with KEYPAD_TYPE="ble_hid")
    # ------------------------------------------------------------------
    "BLE_KP_MAC": "XX:XX:XX:XX:XX:XX",
    "KEY_DEBOUNCE_MS": 0,

    # ------------------------------------------------------------------
    # OLED display (used with DISPLAY_TYPE="oled")
    # ------------------------------------------------------------------
    "OLED": {
        # Interface: "SPI" (SSD1309, default) or "I2C" (SSD1306)
        "BUS": "SPI",

        # Controller: "SSD1309" | "SSD1306" | "SH1106"
        # SSD1309 and SSD1306 use the same commands.
        # SH1106 has a different column offset (+2) in the page routine.
        "CONTROLLER": "SSD1309",

        # Display resolution (in pixels)
        "WIDTH":  128,
        "HEIGHT": 64,

        # OLED rendering method
        "USE_GLYPHS": True,

        # SPI pins (used when BUS="SPI")
        "SCK_PIN":  18,   # clock
        "MOSI_PIN": 23,   # data
        "DC_PIN":   21,   # data/command
        "CS_PIN":   5,    # chip select
        "RST_PIN":  22,   # reset (optional, -1 to disable)

        # I2C pins (used when BUS="I2C")
        "SCL_PIN":  22,
        "SDA_PIN":  21,
        "I2C_ADDR": 0x3C,  # typical for SSD1306; 0x3D if JP1 is open
    },

    # ------------------------------------------------------------------
    # I2C LCD display (used with DISPLAY_TYPE="lcd")
    # ------------------------------------------------------------------
    "LCD": {
        "SCL_PIN":  22,
        "SDA_PIN":  21,
        "I2C_ADDR": 0x27,
        "COLS":     16,
        "ROWS":     2,
    },

    # ------------------------------------------------------------------
    # GPIO matrix keypad (used with KEYPAD_TYPE="matrix")
    # ------------------------------------------------------------------
    "KEYPAD": {
        "ROW_PINS": [32, 33, 18, 19],
        "COL_PINS": [26, 27, 23, 25],
        "KEY_DEBOUNCE_MS": 50,

        "PRIMARY_MAP": {
            "K_1": "1", "K_2": "2", "K_3": "3", "K_4": "4",
            "K_5": "5", "K_6": "6", "K_7": "7", "K_8": "8",
            "K_9": "9", "K_0": "0",
            "K_STAR":      "CMD_SHIFT_A",
            "K_POUND":     "CMD_SHIFT_B",
            "K_ENTER":     "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE":    "CMD_DELETE",
            "K_SHIFT":     "CMD_CLEAR",
        },

        "SHIFT_A_MAP": {
            "K_1": "(", "K_2": ")", "K_3": "+", "K_4": "-",
            "K_5": "*", "K_6": "/", "K_7": "^", "K_8": "x",
            "K_9": "9", "K_0": "0",
            "K_STAR":      "CMD_SHIFT_A",
            "K_POUND":     "CMD_SHIFT_B",
            "K_ENTER":     "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE":    "CMD_DELETE",
            "K_SHIFT":     "CMD_CLEAR",
        },

        "SHIFT_B_MAP": {
            "K_1": "CMD_LEFT",  "K_2": "CMD_RIGHT",
            "K_3": "CMD_UP",    "K_4": "CMD_DOWN",
            "K_5": ">",  "K_6": "<",
            "K_7": ">=", "K_8": "<=",
            "K_9": "!=", "K_0": "=",
            "K_STAR":      "CMD_SHIFT_A",
            "K_POUND":     "CMD_SHIFT_B",
            "K_ENTER":     "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE":    "CMD_DELETE",
            "K_SHIFT":     "CMD_CLEAR",
        },
    },
}