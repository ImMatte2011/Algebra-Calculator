"""
config.py — Hardware configuration for the ESP32 firmware.

To change the hardware variant, edit only this file.
The rest of the firmware (main.py, drivers, etc.) should not be touched.

KEYPAD_TYPE:  "ble_hid"  → BLE HID macropad
              "matrix"   → 4x4 matrix keypad via GPIO
DISPLAY_TYPE: "oled"        → OLED display SSD1309/SSD1306/SH1106
              "lcd"         → 16x2 I2C LCD display
              "tft"         → ST7796 TFT connected to this ESP32
              "tft_remote"  → TFT/touch on a second ESP32 over UART
"""

try:
    import settings
except ImportError as exc:
    missing_module = getattr(exc, "name", None)
    if (missing_module != "settings"
            and (missing_module is not None or "settings" not in str(exc))):
        raise
    settings = None

if settings is None:
    BLE_KP_MAC = ""
elif not hasattr(settings, "BLE_KP_MAC"):
    raise ValueError("Add BLE_KP_MAC to firmware_esp32/settings.py")
else:
    BLE_KP_MAC = settings.BLE_KP_MAC


CONFIG = {
    # ------------------------------------------------------------------
    # Selected hardware (change only these two to switch variants)
    # ------------------------------------------------------------------
    "KEYPAD_TYPE":  "ble_hid",  # "ble_hid" | "matrix"
    "DISPLAY_TYPE": "oled",     # "oled" | "lcd" | "tft" | "tft_remote"

    # ------------------------------------------------------------------
    # Watchdog timer (enabled by default, can be disabled for debugging)
    # ------------------------------------------------------------------
    "ENABLE_WATCHDOG":     True,
    "WATCHDOG_TIMEOUT_MS": 60000,

    # ------------------------------------------------------------------
    # BLE toward the phone (peripheral — always used)
    # ------------------------------------------------------------------
    "BLE_NAME":            "CALC-ESP32",
    "BLE_SERVICE_UUID":    "22337400-2cf2-4bed-8172-a832e5ba8d1f",
    "BLE_EXPR_CHAR_UUID":  "6ee3cd41-4e4c-4bdb-809e-d45007604f4a",
    "BLE_RESULT_CHAR_UUID":"062251c8-1b65-47a2-83a4-4f50b781a158",
    "PHONE_MAC":           "XX:XX:XX:XX:XX:XX",
    "BLE_PHONE_TIMEOUT_S": 30,

    # ------------------------------------------------------------------
    # BLE HID macropad (central — used only with KEYPAD_TYPE="ble_hid")
    # ------------------------------------------------------------------
    "BLE_KP_MAC": BLE_KP_MAC,
    "KEY_DEBOUNCE_MS": 0,                # handled by the macropad itself

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

        "WIDTH":  128,
        "HEIGHT": 64,

        # OLED rendering method
        "USE_GLYPHS": True,

        # SPI pins (used when BUS="SPI")
        "SCK_PIN":  18,   # clock
        "MOSI_PIN": 23,   # data
        "DC_PIN":   21,   # data/command
        "CS_PIN":   5,    # chip select
        "RST_PIN":  22,   # reset (opzionale, -1 per disabilitare)

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
    # TFT display ST7796 (used with DISPLAY_TYPE="tft") — E32R35T board
    # ------------------------------------------------------------------
    "TFT": {
        "WIDTH":  320,          # native (portrait) size
        "HEIGHT": 480,
        "ROTATION": 1,          # 0/2 portrait, 1/3 landscape
        "BGR": True,            # set False if red/blue are swapped
        "INVERT": False,        # set True if colors look negative
        "USE_GLYPHS": True,
        "BAUDRATE": 40_000_000,
        "SPI_ID": 1,
        "SCK_PIN": 14, "MOSI_PIN": 13, "MISO_PIN": 12,
        "CS_PIN": 15, "DC_PIN": 2,
        "RST_PIN": -1,          # tied to EN on this board (software reset used)
        "BL_PIN": 27,
    },

    # UART link between the calculator ESP32 and the TFT ESP32.
    # Configure the same UART ID, pins and baud rate on both boards.
    # Connect TX to the other board's RX, RX to TX, and GND to GND.
    "TFT_LINK": {
        "UART_ID": 2,
        "TX_PIN": 17,
        "RX_PIN": 16,
        "BAUDRATE": 921600,
    },

    # Resistive touch XPT2046 (shares the TFT SPI bus)
    "TOUCH": {
        "ENABLED": True,
        "CS_PIN": 33, "IRQ_PIN": 36,
        "BAUDRATE": 2_000_000,
        # Calibration: raw 12-bit values AFTER the optional axis swap.
        # Measure with tests/test_tft.py (tap the 4 corners).
        "SWAP_XY": True, "INVERT_X": False, "INVERT_Y": False,
        "X_MIN": 200, "X_MAX": 3900, "Y_MIN": 200, "Y_MAX": 3900,
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