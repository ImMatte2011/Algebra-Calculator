"""ESP32 configuration.

Values are read from environment variables when available. On MicroPython
`os.getenv` may not exist; in that case the defaults below are used. For
local testing on the host you can create a `.env` file and use python-dotenv
when running CPython tests.
"""
import os

def _getenv(key, default=None):
    try:
        return os.getenv(key, default)
    except Exception:
        # MicroPython's `os` may not implement getenv
        try:
            return os.environ.get(key, default)
        except Exception:
            return default

CONFIG = {
    "BLE_NAME": _getenv("BLE_NAME", "CALC-ESP32"),
    "BLE_SERVICE_UUID": _getenv("BLE_SERVICE_UUID", "12345678-1234-5678-1234-56789abcdef0"),
    "BLE_EXPR_CHAR_UUID": _getenv("BLE_EXPR_CHAR_UUID", "12345678-1234-5678-1234-56789abcdef1"),
    "BLE_RESULT_CHAR_UUID": _getenv("BLE_RESULT_CHAR_UUID", "12345678-1234-5678-1234-56789abcdef2"),
    "DISPLAY_WIDTH": int(_getenv("DISPLAY_WIDTH", 128)),
    "DISPLAY_HEIGHT": int(_getenv("DISPLAY_HEIGHT", 64)),
    "KEY_DEBOUNCE_MS": int(_getenv("KEY_DEBOUNCE_MS", 50)),
}
