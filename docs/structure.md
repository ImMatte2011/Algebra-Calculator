# Project Structure

- Cartelle separate per ESP32, RPi4 e Android: interpreti, toolchain e librerie diversi.
- Una cartella per la documentazione (`docs/`).
- Vedi [../README.md](../README.md) per la panoramica generale.

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
│       ├── ci.yml              # CI Python (backend_rpi4)
│       └── android-ci.yml      # CI Android (android-app)
│
├── caddy/
│   └── Caddyfile
│
├── scripts/
│   └── deploy_esp32.py
│
├── android-app/                # App Android bridge BLE ↔ HTTP
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
│           ├── test/                       # unit test (JVM, no emulatore)
│           │   └── java/com/myne/alg_calc/
│           │       ├── ble/
│           │       │   └── BlePacketParserTest.kt
│           │       └── network/
│           │           └── ApiServiceTest.kt
│           └── androidTest/                # instrumented test (emulatore)
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
- MVVM: `MainViewModel` orchestration, `BleManager` per il BLE, `ApiService`
  (Retrofit) per il server

### `ble/`
`BleManager`: connessione GATT, permessi runtime (Android 12+ vs precedenti),
riconnessione automatica con backoff, esposizione stato come `StateFlow`.
`BleConnectionState`: sealed class per lo stato tipizzato.
`BlePacketParser`: parsing dei pacchetti-tupla Python inviati dall'ESP32.

### `network/`
`ApiService`: client Retrofit con timeout espliciti, interceptor per il Bearer
token (opzionale) e logging BASIC (non loga i corpi, per non esporre dati in
Logcat).

### `settings/`
`AppSettings`: configurazione persistita in SharedPreferences (MAC ESP32, URL
RPi4, token API). Nessun valore reale hardcoded nel sorgente.

### `data/`
`MathRequest` / `MathResponse`: modelli JSON. `LogEntry`: log tipizzato per
la UI (BLE_IN, BLE_OUT, NET_OUT, NET_IN, INFO, ERROR).

---

## ESP32 — `firmware_esp32/`

- MicroPython
- `ble/ble_bridge.py`: bridge BLE verso l'app Android
- `drivers/`: LCD I2C, tastiera 4x4 a doppio SHIFT, scroller testo
- `core/input_handler.py`: stato espressione, cursore, menu
- `docs/`: mappa tastiera doppio SHIFT

---

## Raspberry Pi 4 — `backend_rpi4/`

- Python 3.11+ / FastAPI / SymPy
- `main.py`: FastAPI app (`/solve`, `/status`)
- `config.py`: `ACCESS_MODE` (`public` | `tailscale`) e `API_TOKEN`
- `utils/validators.py`: verifica Bearer token condizionata da `ACCESS_MODE`
- `math_engine/`: parser + solver SymPy per espressioni, equazioni, disequazioni

---

## Altre cartelle

- `docs/` — documentazione
- `caddy/` — reverse proxy HTTPS (usato con `ACCESS_MODE=public`)
- `scripts/` — `deploy_esp32.py`: genera `firmware_esp32/settings.py` da `.env.esp32`
