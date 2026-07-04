# ESP32 Settings

The ESP32 firmware is configured mainly through `firmware_esp32/config.py`.
The ESP32 does not store the Raspberry Pi URL and does not call `/solve`
directly. Backend URL, access mode, and bearer token belong to the Android app
and Raspberry Pi backend configuration.

## Hardware Selection

Change these values in `firmware_esp32/config.py` to select the active ESP32
hardware variant:

```python
CONFIG = {
    "KEYPAD_TYPE": "ble_hid",  # "ble_hid" or "matrix"
    "DISPLAY_TYPE": "oled",   # "oled" or "lcd"
}
```

`KEYPAD_TYPE="ble_hid"` means the ESP32 reads a BLE HID macropad as a central
device, then switches to the Android BLE bridge when it needs to send a math
request.

`KEYPAD_TYPE="matrix"` means the ESP32 reads the local GPIO matrix keypad and
uses the Android BLE bridge directly.

## Android BLE Bridge Settings

These values identify the BLE peripheral service exposed by the ESP32 to the
Android app:

```python
"BLE_NAME": "CALC-ESP32",
"BLE_SERVICE_UUID": "...",
"BLE_EXPR_CHAR_UUID": "...",
"BLE_RESULT_CHAR_UUID": "...",
```

The Android app must be configured with the ESP32 MAC address and the matching
BLE UUIDs expected by the app code.

## Optional Generated Settings

`scripts/deploy_esp32.py` can generate `firmware_esp32/settings.py` from
`.env.esp32` for deployment-specific values. Keep that file for ESP32-local
settings only, such as BLE names or UUIDs. Do not use it to describe an
ESP32-to-Raspberry WiFi architecture.

If you generate files that contain secrets or device-specific values, do not
commit them.

## Backend Settings Live Elsewhere

Configure the backend and Android app separately:

- backend access mode and token: `.env`, `backend_rpi4/config.py`;
- Android app URL/token/MAC: the app settings screen;
- public HTTPS and DuckDNS: `caddy/Caddyfile` plus DNS setup, only for
  `ACCESS_MODE=public`.
