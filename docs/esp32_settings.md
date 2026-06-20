# firmware_esp32/settings.py e script di deploy

`./scripts/deploy_esp32.py` legge un file `.env.esp32` e genera
`firmware_esp32/settings.py`.

Formato del file generato (compatibile MicroPython):

```
# Auto-generated settings for ESP32 (MicroPython friendly)
API_TOKEN = "replace_with_secure_token"
API_URL = "http://192.168.1.100:8000/solve"
WIFI_SSID = "YourSSID"
WIFI_PASSWORD = "YourWifiPassword"
BLE_NAME = "CALC-ESP32"
...
```

## Come usarlo

1. Copia `.env.esp32.example` → `.env.esp32` e modifica i valori.
2. Esegui:

```bash
python scripts/deploy_esp32.py --env .env.esp32 --out firmware_esp32/settings.py
```

3. Copia `firmware_esp32/settings.py` sul filesystem dell'ESP32 (es. con
   `ampy` o `rshell`), oppure includilo nell'immagine firmware.

## Nota di sicurezza

Non committare `firmware_esp32/settings.py` con segreti reali nel controllo
versione — è già escluso da `.gitignore` (`.env*`), ma verificalo prima di
ogni push se lo generi in una posizione diversa.
