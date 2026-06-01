# Setup and Configuration

## RPi 4

1. Installare Python 3.11.
2. Creare un ambiente virtuale:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Avviare l`API:

```bash
uvicorn rpi4.main:app --host 127.0.0.1 --port 8000
```

4. Configurare `config.py` con un token sicuro.

## ESP32

1. Copiare i file MicroPython su ESP32.
2. Configurare il display OLED e il keypad secondo i pin.
3. Se disponibile, installare il modulo `ssd1306`.
4. Eseguire `main.py` dall`ESP32.

## Telefono Android

1. Creare un bridge BLE che riceve l`input dall`ESP32.
2. Inviare la richiesta a `https://<server>/solve` con il token Bearer.
3. Restituire il risultato all`ESP32`.

## Docker

1. Costruire l`immagine RPi:

```bash
docker compose build
```

2. Avviare i servizi:

```bash
docker compose up
```

## Caddy / HTTPS

1. Creare un `Caddyfile` e impostare il reverse proxy verso `127.0.0.1:8000`.
2. Esporre solo la porta `443`.
3. Usare DNS dinamico se l`IP cambia.
