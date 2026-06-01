esp32/settings.py and deploy script

`./scripts/deploy_esp32.py` reads a `.env.esp32` file and generates `esp32/settings.py`.

Generated file format (MicroPython friendly):

```
# Auto-generated settings for ESP32 (MicroPython friendly)
API_TOKEN = "replace_with_secure_token"
API_URL = "http://192.168.1.100:8000/solve"
WIFI_SSID = "YourSSID"
WIFI_PASSWORD = "YourWifiPassword"
BLE_NAME = "CALC-ESP32"
...
```

How to use:
1. Copy `.env.esp32.example` → `.env.esp32` and edit values.
2. Run:

```bash
python scripts/deploy_esp32.py --env .env.esp32 --out esp32/settings.py
```

3. Copy `esp32/settings.py` to the ESP32 filesystem (e.g., with `ampy` or `rshell`), or include it in your firmware image.

Security note: do not commit `esp32/settings.py` containing real secrets to version control.
