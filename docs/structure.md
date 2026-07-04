# Project Structure

- Separate folders for ESP32, RPi4 and Android: different interpreters, toolchains and libraries.
- One folder for documentation (`docs/`).
- See [../README.md](../README.md) for the general overview.

## Repository Tree

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
│       ├── ci.yml              # Python CI (backend_rpi4)
│       └── android-ci.yml      # Android CI (android-app)
│
├── caddy/
│   └── Caddyfile
│
├── scripts/
│   └── deploy_esp32.py
│
├── android-app/                # Android BLE ↔ HTTP bridge app
│   ├── .gitignore
│   ├── local.properties.example
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   ├── gradle/
│   │   ├── libs.versions.toml
│   │   └── wrapper/
│   └── app/
│       ├── build.gradle.kts
│       └── src/
│           ├── main/
│           │   ├── AndroidManifest.xml
│           │   └── java/com/myne/alg_calc/
│           │       ├── MainActivity.kt
│           │       ├── MainViewModel.kt
│           │       ├── ble/
│           │       │   ├── BleConnectionState.kt
│           │       │   ├── BleManager.kt
│           │       │   └── BlePacketParser.kt
│           │       ├── data/
│           │       │   ├── LogEntry.kt
│           │       │   └── MathRequest.kt
│           │       ├── network/
│           │       │   └── ApiService.kt
│           │       ├── settings/
│           │       │   └── AppSettings.kt
│           │       └── ui/theme/
│           ├── test/                       # unit tests (JVM, no emulator)
│           │   └── java/com/myne/alg_calc/
│           │       ├── ble/
│           │       │   └── BlePacketParserTest.kt
│           │       └── network/
│           │           └── ApiServiceTest.kt
│           └── androidTest/                # instrumented tests (emulator)
│               └── java/com/myne/alg_calc/
│                   └── ExampleInstrumentedTest.kt
│
├── firmware_esp32/
│   ├── boot.py
│   ├── main.py
│   ├── config.py
│   ├── drivers/
│   ├── core/
│   ├── ble/
│   │   └── ble_bridge.py
│   ├── utils/
│   └── docs/
│       ├── README_KEYPAD.md
│       └── keypad_preview.html
│
├── backend_rpi4/
│   ├── Dockerfile
│   ├── main.py
│   ├── config.py
│   ├── math_engine/
│   ├── utils/
│   └── tests/
│       ├── test_api.py
│       ├── test_auth.py
│       └── test_math_engine.py
│
└── docs/
    ├── structure.md
    ├── server.md
    ├── android_app.md
    ├── esp32_settings.md
    ├── deploy.md
    ├── network.md
    └── setup_and_configure.md
```

## Android — `android-app/`

- Kotlin + Jetpack Compose
- MVVM: `MainViewModel` orchestration, `BleManager` for BLE, `ApiService` (Retrofit) for the server

### `ble/`
`BleManager`: GATT connection, runtime permissions (Android 12+ vs earlier), automatic reconnection with backoff, state exposed as `StateFlow`.
`BleConnectionState`: sealed class for typed state.
`BlePacketParser`: parsing of Python tuple packets sent by the ESP32.

### `network/`
`ApiService`: Retrofit client with explicit timeouts, interceptor for the Bearer token (optional) and BASIC logging (does not log bodies, to avoid exposing data in Logcat).

### `settings/`
`AppSettings`: configuration persisted in SharedPreferences (ESP32 MAC, RPi4 URL, API token). No real value hardcoded in the source.

### `data/`
`MathRequest` / `MathResponse`: JSON models. `LogEntry`: typed log for the UI (BLE_IN, BLE_OUT, NET_OUT, NET_IN, INFO, ERROR).

---

## ESP32 — `firmware_esp32/`

- MicroPython
- `ble/ble_bridge.py`: BLE bridge to the Android app
- `drivers/`: I2C LCD, 4x4 dual-SHIFT keypad, text scroller
- `core/input_handler.py`: expression state, cursor, menu
- `docs/`: dual-SHIFT keypad map

---

## Raspberry Pi 4 — `backend_rpi4/`

- Python 3.11+ / FastAPI / SymPy
- `main.py`: FastAPI app (endpoints `/solve`, `/toggle`, `/status`)
- `config.py`: `ACCESS_MODE` (`public` | `tailscale`) and `API_TOKEN`
- `utils/validators.py`: Bearer token verification conditioned on `ACCESS_MODE`
- `math_engine/`: SymPy parser + solver for expressions, equations, inequalities

---

## Other Folders

- `docs/` — documentation
- `caddy/` — HTTPS reverse proxy (used with `ACCESS_MODE=public`)
- `scripts/` — `deploy_esp32.py`: generates `firmware_esp32/settings.py` from `.env.esp32`