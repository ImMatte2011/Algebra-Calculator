# Project Structure

- Due cartelle separate per ESP32 e Raspberry Pi perché usano interpreti e
  librerie diverse (MicroPython vs CPython).
- Una cartella per la documentazione (`docs/`).
- Vedi [../README.md](../README.md) per la panoramica generale del progetto.

## Albero del repository

```
.
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── .env.example
├── .env.esp32.example
├── pytest.ini
├── requirements.txt
├── docker-compose.yml
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── caddy/
│   └── Caddyfile
│
├── scripts/
│   └── deploy_esp32.py
│
├── firmware_esp32/
│   ├── boot.py
│   ├── main.py
│   ├── config.py
│   ├── drivers/
│   │   ├── display_abstract.py
│   │   ├── display_scroller.py
│   │   ├── i2c_lcd.py
│   │   ├── keypad_abstract.py
│   │   ├── lcd_api.py
│   │   └── lcd_display.py
│   ├── core/
│   │   └── input_handler.py
│   ├── ble/
│   │   └── ble_bridge.py
│   ├── utils/
│   │   ├── helpers.py
│   │   └── logger.py
│   └── docs/
│       ├── README_KEYPAD.md
│       └── keypad_preview.html
│
├── backend_rpi4/
│   ├── Dockerfile
│   ├── main.py                # app FastAPI in esecuzione
│   ├── config.py
│   ├── math_engine/
│   │   ├── engine.py
│   │   ├── parser.py
│   │   └── solver.py
│   ├── utils/
│   │   ├── logger.py
│   │   └── validators.py
│   └── tests/
│       ├── test_api.py
│       ├── test_auth.py
│       └── test_math_engine.py
│
└── docs/
    ├── structure.md
    ├── server.md
    ├── esp32_settings.md
    ├── deploy.md
    ├── network.md
    ├── phone_bridge.md
    └── setup_and_configure.md
```

## ESP32 — `firmware_esp32/`

- MicroPython
- Librerie hardware-specifiche (display I2C, tastiera matriciale, BLE)

### `drivers/`
Driver hardware: display LCD I2C (`lcd_display.py`, `i2c_lcd.py`,
`lcd_api.py`), tastiera matriciale 4x4 con doppio SHIFT
(`keypad_abstract.py`), scorrimento testo su display limitato
(`display_scroller.py`), interfaccia astratta del display
(`display_abstract.py`).

### `core/`
Logica applicativa indipendente dall'hardware: gestione dello stato
dell'espressione, del cursore e dei menu (`input_handler.py`).

### `ble/`
Bridge Bluetooth Low Energy verso il telefono Android (`ble_bridge.py`),
con gestione della riconnessione su invio fallito.

### `utils/`
Funzioni di supporto: logging (`logger.py`), normalizzazione delle
espressioni (`helpers.py`).

### `docs/`
Documentazione specifica del firmware ESP32: mappa della tastiera a doppio
SHIFT (`README_KEYPAD.md`) e anteprima visiva interattiva
(`keypad_preview.html`).

---
## Raspberry Pi 4 — `backend_rpi4/`

- Python 3.11+
- Server FastAPI + motore di algebra simbolica (SymPy)

### `math_engine/`
Parsing (`parser.py`) e risoluzione (`solver.py`) di espressioni, equazioni
e disequazioni con SymPy; orchestrazione (`engine.py`).

### `utils/`
Logging (`logger.py`) e validazione del Bearer token, condizionata da
`ACCESS_MODE` (`validators.py`).

### `tests/`
Test pytest per API, autenticazione e motore matematico.

### root del pacchetto
`main.py` (app FastAPI avviata da `uvicorn`), `config.py` (caricamento
configurazione da variabili d'ambiente, incluso `ACCESS_MODE`).

---
## Altre cartelle nella root del repo

- `docs/` — documentazione di progetto (rete, deploy, server, ESP32, ecc.)
- `caddy/` — `Caddyfile` per il reverse proxy HTTPS
- `scripts/` — script di utilità, es. `deploy_esp32.py` per generare
  `firmware_esp32/settings.py` da un file `.env.esp32`
