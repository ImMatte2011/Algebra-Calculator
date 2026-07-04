# Setup and Configuration

Quick step-by-step guide. For details on each component see the linked documents.

## RPi 4

1. Install Python 3.11+.
2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set `API_TOKEN` and `ACCESS_MODE` (see [deploy.md](deploy.md)).
4. Start the API:

```bash
uvicorn backend_rpi4.main:app --host 127.0.0.1 --port 8000
```

Full details: [server.md](server.md).

## ESP32

1. Copy the MicroPython files from `firmware_esp32/` to the ESP32.
2. Configure the OLED/LCD display and keypad according to the pins in `firmware_esp32/config.py`.
3. If available, install the `ssd1306` module (or the equivalent for your display).
4. Generate `firmware_esp32/settings.py` from `.env.esp32` — see [esp32_settings.md](esp32_settings.md).
5. Run `main.py` on the ESP32.

## Android Phone

1. Create a BLE bridge that receives input from the ESP32.
2. Send the request to `https://<server>/solve` with the header `Authorization: Bearer <token>` (only if `ACCESS_MODE=public`).
3. Return the result to the ESP32.

Details: [phone_bridge.md](phone_bridge.md).

## Docker

1. Build the image:

```bash
docker compose build
```

2. Start the services:

```bash
docker compose up
```

## Caddy / HTTPS (only if `ACCESS_MODE=public`)

1. Configure `caddy/Caddyfile` with the reverse proxy pointing to `127.0.0.1:8000`.
2. Expose only port `443`.
3. Use dynamic DNS (e.g. DuckDNS) if your IP changes.

Details: [deploy.md](deploy.md).