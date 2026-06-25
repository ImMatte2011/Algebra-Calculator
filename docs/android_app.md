# App Android — Bridge BLE ↔ HTTP (`android-app/`)

L'app fa da ponte tra l'ESP32 (BLE) e il server FastAPI sul Raspberry Pi
(HTTP/HTTPS): riceve l'espressione via BLE, la inoltra a `/solve`, e rimanda
il risultato all'ESP32 via BLE per visualizzarlo sul display LCD.

Vedi [phone_bridge.md](phone_bridge.md) per l'architettura generale e
[server.md](server.md) per il contratto dell'API.

## Stack e architettura

- **Kotlin** + **Jetpack Compose**
- **MVVM**: `MainViewModel` (logica), `BleManager` (BLE), `ApiService`
  (HTTP Retrofit), `AppSettings` (configurazione)
- **Coroutines + Flow**: pipeline BLE → HTTP → risposta senza callback
  annidate; lo stato è esposto come `StateFlow<UiState>` — la UI non ha
  logica, solo osserva e reagisce
- `BleConnectionState` sealed class: lo stato BLE è tipizzato, non una
  stringa di log — la UI può reagire con colori/pulsanti diversi per
  ogni stato

## Configurazione e segreti

Tutti i valori configurabili (MAC dell'ESP32, URL del RPi, token API)
sono persistiti in **SharedPreferences** tramite `AppSettings` e modificabili
dalla schermata impostazioni dentro l'app. **Nessun valore reale è
hardcoded nel sorgente.**

Alla prima apertura, l'app mostra uno stato "non configurato" finché
l'utente non imposta almeno il MAC e l'URL.

### Token API (`apiToken`)

Il token Bearer è opzionale lato app — viene aggiunto all'header
`Authorization: Bearer <token>` solo se non è vuoto. Questo permette
di usare la stessa app con entrambe le modalità server:

- `ACCESS_MODE=public` (Caddy su HTTPS): imposta il token nelle impostazioni
- `ACCESS_MODE=tailscale` (rete Tailscale): lascia il token vuoto

### `local.properties`

Contiene il percorso all'Android SDK — generato automaticamente da Android
Studio, non va mai committato (già escluso da `.gitignore`). Un file
`local.properties.example` committato serve da template.

## Permessi Bluetooth

La gestione varia tra versioni Android, ed è già implementata in
`BleManager.requiredPermissions()`:

```kotlin
// BleManager.kt — già implementato
fun requiredPermissions(): Array<String> =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        arrayOf(BLUETOOTH_SCAN, BLUETOOTH_CONNECT)        // Android 12+
    } else {
        arrayOf(ACCESS_FINE_LOCATION)                      // Android < 12
    }
```

Il Manifest dichiara entrambi i set. `BLUETOOTH_SCAN` usa
`android:usesPermissionFlags="neverForLocation"` per evitare che il sistema
pensi che l'app usi il BLE per geolocalizzazione.

## `android:usesCleartextTraffic="true"`

Attualmente presente nel Manifest per permettere HTTP in chiaro verso il
Raspberry Pi via Tailscale (la cifratura è a livello rete, non applicativo).
Se/quando si passa a `ACCESS_MODE=public` con Caddy su HTTPS, questo flag
va rimosso (o ristretto a soli host locali via `network_security_config.xml`).

## Test automatici

### Unit test — `app/src/test/` (JVM, senza emulatore)

Girano velocemente in CI senza emulatore. Coprono la logica pura:

- **`BlePacketParserTest`**: parsing di tutti i formati di pacchetti BLE
  (equazione, disequazione, espressione con azione, parentesi nell'espressione,
  casi di errore)
- **`ApiServiceTest`**: client HTTP con `MockWebServer` — verifica che il
  token sia aggiunto correttamente all'header, gestione 200/401/timeout

Per aggiungerli: vedi [Come aggiungere i test](#come-aggiungere-i-test).

### Instrumented test — `app/src/androidTest/` (emulatore)

Il vero hardware BLE non è testabile in CI headless. Strategia:
- La UI e il `ViewModel` si testano con un `FakeBleManager` che implementa
  la stessa interfaccia di `BleManager` (da implementare quando l'architettura
  si consolida)
- Il test con hardware BLE reale rimane manuale, su device fisico

### CI

Workflow dedicato `.github/workflows/android-ci.yml` — separato da quello
Python, si triggera solo quando cambiano file in `android-app/`:

```
git push  →  cambia android-app/  →  android-ci.yml esegue testDebugUnitTest + lintDebug
git push  →  cambia backend_rpi4/ →  ci.yml esegue pytest
```

## Come aggiungere i test

### 1. Dipendenze di test (`app/build.gradle.kts`)

Aggiungi nelle `dependencies {}` (le due righe di `testImplementation`
sono quelle nuove — le altre sono già presenti):

```kotlin
dependencies {
    // ... dipendenze esistenti ...
    testImplementation(libs.junit)

    // MockWebServer per testare il client HTTP senza server reale
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")

    // Coroutines test per testare suspend functions
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
}
```

### 2. Crea i file di test

Posizionali esattamente in questi percorsi (crea le cartelle se non esistono):

```
android-app/app/src/test/java/com/myne/alg_calc/ble/BlePacketParserTest.kt
android-app/app/src/test/java/com/myne/alg_calc/network/ApiServiceTest.kt
```

Il contenuto di entrambi è nei file scaricabili — vedi la sezione
"Test automatici" nel repo.

### 3. Esegui i test

```bash
cd android-app

# Tutti i unit test
./gradlew testDebugUnitTest

# Solo un file specifico
./gradlew testDebugUnitTest --tests "com.myne.alg_calc.ble.BlePacketParserTest"

# Lint
./gradlew lintDebug
```

In Android Studio: clic destro su un file di test → "Run".

I risultati HTML sono in:
`app/build/reports/tests/testDebugUnitTest/index.html`