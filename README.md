# Calcolatrice Algebrica — ESP32 + Raspberry Pi

Calcolatrice algebrica con tastiera/display su ESP32, che invia le espressioni
via BLE a un telefono Android (bridge), il quale le inoltra via HTTPS a un
server FastAPI su Raspberry Pi 4 (nel mio caso) dove SymPy risolve equazioni,
disequazioni ed espressioni.

```
ESP32 (tastiera + LCD) --BLE--> Telefono (bridge) --HTTPS--> FastAPI (RPi4) --> SymPy
```

> Progetto personale, ancora in sviluppo attivo — vedi
> [CONTRIBUTING.md](CONTRIBUTING.md) per lo stato attuale riguardo a
> contributi esterni.

## Struttura del repository

```
.
├── backend_rpi4/         # Server FastAPI + motore algebrico (SymPy)
├── firmware_esp32/       # Firmware MicroPython per l'ESP32
├── caddy/                # Configurazione reverse proxy HTTPS
├── docs/                 # Documentazione di progetto
├── scripts/              # Script di utilità (deploy ESP32)
├── docker-compose.yml
└── requirements.txt
```

Dettaglio completo cartella per cartella: [docs/structure.md](docs/structure.md)

## Documentazione

- **Server (RPi4 / FastAPI)**: [docs/server.md](docs/server.md)
- **Impostazioni ESP32**: [docs/esp32_settings.md](docs/esp32_settings.md)
- **Tastiera ESP32 (doppio SHIFT)**: [firmware_esp32/docs/README_KEYPAD.md](firmware_esp32/docs/README_KEYPAD.md)
- **Architettura di rete e sicurezza**: [docs/network.md](docs/network.md)
- **Bridge telefono Android**: [docs/phone_bridge.md](docs/phone_bridge.md)
- **Deploy e sicurezza (Caddy, Docker, accesso pubblico vs Tailscale)**: [docs/deploy.md](docs/deploy.md)
- **Setup completo passo-passo**: [docs/setup_and_configure.md](docs/setup_and_configure.md)
- **Struttura del progetto**: [docs/structure.md](docs/structure.md)

## Quick start (server)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # poi imposta API_TOKEN e ACCESS_MODE
uvicorn backend_rpi4.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
pytest backend_rpi4/tests -q
```

## Accesso: pubblico vs Tailscale

Il server supporta due modalità di esposizione alternative, scelte tramite
la variabile d'ambiente `ACCESS_MODE` (vedi [docs/deploy.md](docs/deploy.md)
per i dettagli):

- `ACCESS_MODE=public` *(default)* — il Pi è raggiungibile da Internet
  dietro Caddy su `:443`. Il Bearer token (`API_TOKEN`) è **obbligatorio**
  su ogni richiesta.
- `ACCESS_MODE=tailscale` — il Pi è raggiungibile solo dalla tua tailnet
  Tailscale, che fa già da perimetro di accesso. Il token non viene
  verificato.

## Licenza

Vedi [LICENSE](LICENSE) — codice proprietario, "tutti i diritti
riservati". Non è una libreria open source: il repo è pubblico a scopo
dimostrativo/portfolio.
