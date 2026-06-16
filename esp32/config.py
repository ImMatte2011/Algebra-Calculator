CONFIG = {
    "BLE_NAME": "CALC-ESP32"
    "BLE_SERVICE_UUID": "YOUR_SERVICE_UUID"
    "BLE_EXPR_CHAR_UUID": "YOUR_EXPR_CHAR_UUID"
    "BLE_RESULT_CHAR_UUID": "YOUR_RESULT_CHAR_UUID"

    "KEY_DEBOUNCE_MS": 100

    "LCD": {
        "SCL_PIN": 22,
        "SDA_PIN": 21,
        "I2C_ADDR": 0x27,
        "COLS": 16,
        "ROWS": 2,
    },

    "KEYPAD": {
        "ROW_PINS": [32, 33, 18, 19],
        "COL_PINS": [26, 27, 23, 25],

        "PRIMARY_MAP": {
            "K_1": "1",
            "K_2": "2",
            "K_3": "3",
            "K_4": "4",
            "K_5": "5",
            "K_6": "6",
            "K_7": "7",
            "K_8": "8",
            "K_9": "9",
            "K_0": "0",
            "K_STAR": "CMD_SHIFT_A",
            "K_POUND": "CMD_SHIFT_B",
            "K_ENTER": "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE": "CMD_DELETE",
            "K_SHIFT": "CMD_CLEAR",
        },

        "SHIFT_A_MAP": {
            "K_1": "(",
            "K_2": ")",
            "K_3": "+",
            "K_4": "-",
            "K_5": "*",
            "K_6": "/",
            "K_7": "^",
            "K_8": "x",
            "K_9": "9",
            "K_0": "0",
            "K_STAR": "CMD_SHIFT_A",
            "K_POUND": "CMD_SHIFT_B",
            "K_ENTER": "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE": "CMD_DELETE",
            "K_SHIFT": "CMD_CLEAR",
        },

        "SHIFT_B_MAP": {
            "K_1": "CMD_LEFT",
            "K_2": "CMD_RIGHT",
            "K_3": "CMD_UP",
            "K_4": "CMD_DOWN",
            "K_5": ">",
            "K_6": "<",
            "K_7": ">=",
            "K_8": "<=",
            "K_9": "!=",
            "K_0": "=",
            "K_STAR": "CMD_SHIFT_A",
            "K_POUND": "CMD_SHIFT_B",
            "K_ENTER": "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE": "CMD_DELETE",
            "K_SHIFT": "CMD_CLEAR",
        },
    },
}
