"""
config.py — Configurazione hardware del firmware ESP32.

Per cambiare variante hardware modificare solo questo file.
Il resto del firmware (main.py, driver, ecc.) non va toccato.

KEYPAD_TYPE:  "ble_hid"  → macropad BLE HID
              "matrix"   → tastierino matriciale 4x4 via GPIO
DISPLAY_TYPE: "oled"     → display OLED SSD1309/SSD1306/SH1106
              "lcd"      → display LCD I2C 16x2
"""

CONFIG = {
    # ------------------------------------------------------------------
    # Hardware selezionato (cambia solo questi due per switchare variante)
    # ------------------------------------------------------------------
    "KEYPAD_TYPE":  "ble_hid",  # "ble_hid" | "matrix"
    "DISPLAY_TYPE": "oled",     # "oled"    | "lcd"

    # ------------------------------------------------------------------
    # BLE verso il telefono (peripheral — usato sempre)
    # ------------------------------------------------------------------
    "BLE_NAME":            "CALC-ESP32",
    "BLE_SERVICE_UUID":    "22337400-2cf2-4bed-8172-a832e5ba8d1f",
    "BLE_EXPR_CHAR_UUID":  "6ee3cd41-4e4c-4bdb-809e-d45007604f4a",
    "BLE_RESULT_CHAR_UUID":"062251c8-1b65-47a2-83a4-4f50b781a158",

    # ------------------------------------------------------------------
    # BLE HID macropad (central — usato solo con KEYPAD_TYPE="ble_hid")
    # ------------------------------------------------------------------
    "BLE_KP_MAC": "E0:0F:7A:C3:C9:DF",   # MAC confermato da nRF Connect
    "KEY_DEBOUNCE_MS": 0,                # gestito dal macropad stesso

    # ------------------------------------------------------------------
    # Display OLED (usato con DISPLAY_TYPE="oled")
    # ------------------------------------------------------------------
    "OLED": {
        # Interfaccia: "SPI" (SSD1309, default) o "I2C" (SSD1306)
        "BUS": "SPI",

        # Controller: "SSD1309" | "SSD1306" | "SH1106"
        # SSD1309 e SSD1306 usano gli stessi comandi.
        # SH1106 ha un offset di colonna diverso (+2) nella routine di pagina.
        "CONTROLLER": "SH1106",

        "WIDTH":  128,
        "HEIGHT": 64,

        # Metodo di rendering su OLED
        "USE_GLYPHS": True,

        # Pin SPI (usati quando BUS="SPI")
        "SCK_PIN":  18,   # clock
        "MOSI_PIN": 23,   # data
        "DC_PIN":   21,   # data/command
        "CS_PIN":   5,    # chip select
        "RST_PIN":  22,   # reset (opzionale, -1 per disabilitare)

        # Pin I2C (usati quando BUS="I2C")
        "SCL_PIN":  22,
        "SDA_PIN":  21,
        "I2C_ADDR": 0x3C,  # tipico per SSD1306; 0x3D se JP1 aperto
    },

    # ------------------------------------------------------------------
    # Display LCD I2C (usato con DISPLAY_TYPE="lcd")
    # ------------------------------------------------------------------
    "LCD": {
        "SCL_PIN":  22,
        "SDA_PIN":  21,
        "I2C_ADDR": 0x27,
        "COLS":     16,
        "ROWS":     2,
    },

    # ------------------------------------------------------------------
    # Tastierino matriciale GPIO (usato con KEYPAD_TYPE="matrix")
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