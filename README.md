# Calcolatrice Algebrica — ESP32 + Raspberry Pi

Calcolatrice algebrica con tastiera/display su ESP32, che invia le espressioni
via BLE a un telefono Android (bridge), il quale le inoltra via HTTPS a un
server FastAPI su Raspberry Pi 4 (nel mio caso) dove SymPy risolve equazioni,
disequazioni ed espressioni.

```
ESP32 (tastiera + display)
       │  BLE
       ▼
App Android (bridge)
       │  HTTP/HTTPS
       ▼
RPi (FastAPI + SymPy)
       │  (risposta)
       ▼
App Android ──► ESP32 (display)
```

> Progetto personale, ancora in sviluppo attivo — vedi
> [CONTRIBUTING.md](CONTRIBUTING.md) per lo stato attuale riguardo a
> contributi esterni.

## Struttura del repository

```
.
├── android-app/         # App Android bridge BLE ↔ HTTP (Kotlin + Compose)
├── backend_rpi4/         # Server FastAPI + motore algebrico (SymPy)
├── firmware_esp32/       # Firmware MicroPython per l'ESP32
├── caddy/                # Configurazione reverse proxy HTTPS
├── docs/                 # Documentazione di progetto
├── scripts/              # Script di utilità (deploy ESP32)
├── docker-compose.yml
└── requirements.txt
```

Dettaglio completo: [docs/structure.md](docs/structure.md)

## Documentazione

- **Server (RPi4 / FastAPI)**: [docs/server.md](docs/server.md)
- **Impostazioni ESP32**: [docs/esp32_settings.md](docs/esp32_settings.md)
- **Architettura di rete e sicurezza**: [docs/network.md](docs/network.md)
- **Bridge telefono Android**: [docs/android_app.md](docs/android_app.md)
- **Deploy e sicurezza (Caddy, Docker, accesso pubblico vs Tailscale)**: [docs/deploy.md](docs/deploy.md)
- **Setup completo passo-passo**: [docs/setup_and_configure.md](docs/setup_and_configure.md)
- **Struttura del progetto**: [docs/structure.md](docs/structure.md)

## Quick start
### Server (RPi)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # poi imposta API_TOKEN e ACCESS_MODE
uvicorn backend_rpi4.main:app --reload --host 127.0.0.1 --port 8000
# Esegui i tests per verificare il corretto funzionamento del server
pytest backend_rpi4/tests -q
```

### App Android

Apri `android-app/` in Android Studio. Alla prima apertura dell'app configura
dalla schermata impostazioni: indirizzo MAC dell'ESP32, URL del Raspberry Pi
(con porta), e il token API se il server gira con `ACCESS_MODE=public`.

```bash
cd android-app
./gradlew testDebugUnitTest   # unit test (JVM, no emulatore)
./gradlew lintDebug
```

## Accesso: pubblico vs Tailscale

Il server supporta due modalità di esposizione alternative, scelte tramite
la variabile d'ambiente `ACCESS_MODE` (vedi [docs/deploy.md](docs/deploy.md)
per i dettagli):

| `ACCESS_MODE` | Infrastruttura | Token obbligatorio |
|---|---|---|
| `public` *(default)* | Caddy su `:443`, IP pubblico + DuckDNS | Sì (`API_TOKEN`) |
| `tailscale` | Solo dentro la tailnet Tailscale | No |

## Licenza

Vedi [LICENSE](LICENSE) — codice proprietario, "tutti i diritti
riservati". Non è una libreria open source: il repo è pubblico a scopo
dimostrativo/portfolio.
