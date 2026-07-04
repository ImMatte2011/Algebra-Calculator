# firmware_esp32/settings.py and Deploy Script

`./scripts/deploy_esp32.py` reads a `.env.esp32` file and generates `firmware_esp32/settings.py`.

Format of the generated file (MicroPython-compatible):

```
# Auto-generated settings for ESP32 (MicroPython friendly)
API_TOKEN = "replace_with_secure_token"
API_URL = "http://192.168.1.100:8000/solve"
WIFI_SSID = "YourSSID"
WIFI_PASSWORD = "YourWifiPassword"
BLE_NAME = "CALC-ESP32"
...
```

## How to Use It

1. Copy `.env.esp32.example` → `.env.esp32` and edit the values.
2. Run:

```bash
python scripts/deploy_esp32.py --env .env.esp32 --out firmware_esp32/settings.py
```

3. Copy `firmware_esp32/settings.py` to the ESP32 filesystem (e.g. with `ampy` or `rshell`), or include it in the firmware image.

## Security Note

Do not commit `firmware_esp32/settings.py` with real secrets to version control — it is already excluded by `.gitignore` (`.env*`), but verify this before every push if you generate it in a different location.