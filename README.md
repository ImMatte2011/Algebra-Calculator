# Calc Algebraica - ESP32 + Android + Raspberry Pi

Personal algebra calculator with keypad/display input on ESP32, an Android BLE
bridge, and a Raspberry Pi 4 FastAPI backend powered by SymPy.

```text
ESP32 keypad/display
        |
        | BLE
        v
Android app
        |
        | HTTP/HTTPS, configured in the app
        v
Raspberry Pi 4 (FastAPI + SymPy)
        |
        | result
        v
Android app -> BLE -> ESP32 display
```

The ESP32 does not call the Raspberry Pi directly over WiFi. The Android app
bridges BLE packets to the backend. Public HTTPS with Caddy, DuckDNS, and a
bearer token is used only when the backend runs with `ACCESS_MODE=public`.

> Personal project, still under active development. See
> [CONTRIBUTING.md](CONTRIBUTING.md) for the current policy on external
> contributions.

## Repository Structure

```text
.
├── android-app/          # Android BLE <-> HTTP bridge (Kotlin + Compose)
├── backend_rpi4/         # FastAPI server + SymPy algebra engine
├── firmware_esp32/       # ESP32 MicroPython firmware
├── caddy/                # HTTPS reverse proxy config for public mode
├── docs/                 # Project documentation
├── scripts/              # Utility scripts, including ESP32 deployment
├── docker-compose.yml
└── requirements.txt
```

Full details: [docs/structure.md](docs/structure.md)

## Documentation

- **Server (RPi4 / FastAPI)**: [docs/server.md](docs/server.md)
- **ESP32 settings**: [docs/esp32_settings.md](docs/esp32_settings.md)
- **Network architecture and security**: [docs/network.md](docs/network.md)
- **Android bridge**: [docs/android_app.md](docs/android_app.md)
- **Android install**: [docs/install_android.md](docs/install_android.md)
- **Deploy and security**: [docs/deploy.md](docs/deploy.md)
- **Step-by-step setup**: [docs/setup_and_configure.md](docs/setup_and_configure.md)
- **Project structure**: [docs/structure.md](docs/structure.md)

## Quick Start

### Server (RPi)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then set API_TOKEN and ACCESS_MODE
uvicorn backend_rpi4.main:app --reload --host 127.0.0.1 --port 8000
pytest backend_rpi4/tests -q
```

### Android App

Open `android-app/` in Android Studio. On first launch, configure the ESP32 MAC
address, the Raspberry Pi backend URL, and the API token if the backend uses
`ACCESS_MODE=public`.

```bash
cd android-app
./gradlew testDebugUnitTest
./gradlew lintDebug
```

## Access Modes

The backend supports two alternative access modes through `ACCESS_MODE`:

| `ACCESS_MODE` | Backend exposure | Token |
|---|---|---|
| `public` *(default)* | Caddy on `:443`, public IP/domain such as DuckDNS | Yes (`API_TOKEN`) |
| `tailscale` | Only inside the Tailscale tailnet | No |

The ESP32 side is unchanged in both modes: ESP32 -> BLE -> Android phone.

## License

See [LICENSE](LICENSE). This is proprietary code with all rights reserved. The
repository is public for demonstration/portfolio purposes, not as an open
source library.
