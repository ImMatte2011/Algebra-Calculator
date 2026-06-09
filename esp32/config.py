import os

def _getenv(key, default=None):
    try:
        return os.getenv(key, default)
    except Exception:
        try:
            return os.environ.get(key, default)
        except Exception:
            return default

CONFIG = {
    "BLE_NAME": _getenv("BLE_NAME", "CALC-ESP32"),
    "BLE_SERVICE_UUID": _getenv("BLE_SERVICE_UUID", "12345678-1234-5678-1234-56789abcdef0"),
    "BLE_EXPR_CHAR_UUID": _getenv("BLE_EXPR_CHAR_UUID", "12345678-1234-5678-1234-56789abcdef1"),
    "BLE_RESULT_CHAR_UUID": _getenv("BLE_RESULT_CHAR_UUID", "12345678-1234-5678-1234-56789abcdef2"),
    
    "KEY_DEBOUNCE_MS": int(_getenv("KEY_DEBOUNCE_MS", 50)),
    
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
            "K_STAR": "CMD_SHIFT_A",    # Tasto * attiva lo Shift degli operatori
            "K_POUND": "CMD_SHIFT_B",   # Tasto # attiva lo Shift dei confronti
            "K_ENTER": "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE": "CMD_DELETE",
            "K_SHIFT": "CMD_CLEAR",     # Il vecchio tasto Shift lo ricicliamo come CLEAR!
        },
        
        "SHIFT_A_MAP": {
            "K_1": "(",                 # Parentesi Tonda Aperta!
            "K_2": ")",                 # Parentesi Tonda Chiusa!
            "K_3": "+",
            "K_4": "-",
            "K_5": "*",
            "K_6": "/",
            "K_7": "^",
            "K_8": "x",                 # Incognita 'x'
            "K_9": "9",                 # Fallback ai numeri normali se servono
            "K_0": "0",
            "K_STAR": "CMD_SHIFT_A",    # Premuto di nuovo si disattiva
            "K_POUND": "CMD_SHIFT_B",   # Salta a Shift B
            "K_ENTER": "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE": "CMD_DELETE",
            "K_SHIFT": "CMD_CLEAR",
        },
        
        "SHIFT_B_MAP": {
            "K_1": "CMD_LEFT",          # Le frecce le mettiamo nello Shift B
            "K_2": "CMD_RIGHT",
            "K_3": "CMD_UP",
            "K_4": "CMD_DOWN",
            "K_5": ">",
            "K_6": "<",
            "K_7": ">=",
            "K_8": "<=",
            "K_9": "!=",
            "K_0": "=",
            "K_STAR": "CMD_SHIFT_A",    # Salta a Shift A
            "K_POUND": "CMD_SHIFT_B",   # Premuto di nuovo si disattiva
            "K_ENTER": "CMD_ENTER",
            "K_BACKSPACE": "CMD_BACKSPACE",
            "K_DELETE": "CMD_DELETE",
            "K_SHIFT": "CMD_CLEAR",
        },
    },
}