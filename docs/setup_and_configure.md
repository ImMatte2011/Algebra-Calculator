# Setup and Configuration

Guida rapida passo-passo. Per i dettagli di ogni componente vedi i
documenti linkati.

## RPi 4

1. Installare Python 3.11+.
2. Creare un ambiente virtuale:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Copiare `.env.example` in `.env` e impostare `API_TOKEN` e
   `ACCESS_MODE` (vedi [deploy.md](deploy.md)).
4. Avviare l'API:

```bash
uvicorn backend_rpi4.main:app --host 127.0.0.1 --port 8000
```

Dettagli completi: [server.md](server.md).

## ESP32

1. Copiare i file MicroPython di `firmware_esp32/` sull'ESP32.
2. Configurare il display OLED/LCD e il keypad secondo i pin in
   `firmware_esp32/config.py`.
3. Se disponibile, installare il modulo `ssd1306` (o l'equivalente per il
   proprio display).
4. Generare `firmware_esp32/settings.py` da `.env.esp32` — vedi
   [esp32_settings.md](esp32_settings.md).
5. Eseguire `main.py` dall'ESP32.

## Telefono Android

1. Creare un bridge BLE che riceve l'input dall'ESP32.
2. Inviare la richiesta a `https://<server>/solve` con l'header
   `Authorization: Bearer <token>` (solo se `ACCESS_MODE=public`).
3. Restituire il risultato all'ESP32.

Details: [network.md](network.md).

## Docker

1. Costruire l'immagine:

```bash
docker compose build
```

2. Avviare i servizi:

```bash
docker compose up
```

## Caddy / HTTPS (solo se `ACCESS_MODE=public`)

1. Configurare `caddy/Caddyfile` con il reverse proxy verso
   `127.0.0.1:8000`.
2. Esporre solo la porta `443`.
3. Usare DNS dinamico (es. DuckDNS) se l'IP cambia.

Dettagli: [deploy.md](deploy.md).
