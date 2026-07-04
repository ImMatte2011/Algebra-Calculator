# Android App — BLE ↔ HTTP Bridge (`android-app/`)

The app acts as a bridge between the ESP32 (BLE) and the FastAPI server on the Raspberry Pi (HTTP/HTTPS): it receives the expression via BLE, forwards it to `/solve`, and sends the result back to the ESP32 via BLE for display on the LCD.

See [phone_bridge.md](phone_bridge.md) for the overall architecture and [server.md](server.md) for the API contract.

## Stack and Architecture

- **Kotlin** + **Jetpack Compose**
- **MVVM**: `MainViewModel` (logic), `BleManager` (BLE), `ApiService` (HTTP Retrofit), `AppSettings` (configuration)
- **Coroutines + Flow**: BLE → HTTP → response pipeline without nested callbacks; state is exposed as `StateFlow<UiState>` — the UI has no logic, it only observes and reacts
- `BleConnectionState` sealed class: BLE state is typed, not a log string — the UI can react (colours, buttons) differently for each state

## Configuration and Secrets

All configurable values (ESP32 MAC address, RPi URL, API token) are persisted in **SharedPreferences** via `AppSettings` and can be modified from the in-app settings screen. **No real value is hardcoded in the source.**

On first launch, the app shows a "not configured" state until the user sets at least the MAC address and the URL.

### API Token (`apiToken`)

The Bearer token is optional on the app side — it is added to the `Authorization: Bearer <token>` header only if non-empty. This allows the same app to work with both server modes:

- `ACCESS_MODE=public` (Caddy on HTTPS): set the token in the settings
- `ACCESS_MODE=tailscale` (Tailscale network): leave the token field empty

### `local.properties`

Contains the path to the Android SDK — generated automatically by Android Studio, must never be committed (already excluded by `.gitignore`). A committed `local.properties.example` file serves as a template.

## Bluetooth Permissions

Handling varies across Android versions and is already implemented in `BleManager.requiredPermissions()`:

```kotlin
// BleManager.kt — already implemented
fun requiredPermissions(): Array<String> =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        arrayOf(BLUETOOTH_SCAN, BLUETOOTH_CONNECT)        // Android 12+
    } else {
        arrayOf(ACCESS_FINE_LOCATION)                      // Android < 12
    }
```

The Manifest declares both sets. `BLUETOOTH_SCAN` uses `android:usesPermissionFlags="neverForLocation"` to prevent the system from assuming the app uses BLE for geolocation.

## `android:usesCleartextTraffic="true"`

Currently present in the Manifest to allow plain HTTP to the Raspberry Pi over Tailscale (encryption is at the network layer, not application layer). If/when switching to `ACCESS_MODE=public` with Caddy on HTTPS, this flag should be removed (or restricted to local hosts only via `network_security_config.xml`).

## Automated Tests

### Unit tests — `app/src/test/` (JVM, no emulator)

Run quickly in CI without an emulator. Cover pure logic:

- **`BlePacketParserTest`**: parsing of all BLE packet formats (equation, inequality, expression with action, parentheses in expression, error cases)
- **`ApiServiceTest`**: HTTP client with `MockWebServer` — verifies the token is correctly added to the header, handles 200/401/timeout

To add them: see [How to add tests](#how-to-add-tests).

### Instrumented tests — `app/src/androidTest/` (emulator)

Real BLE hardware is not testable in headless CI. Strategy:
- The UI and `ViewModel` are tested with a `FakeBleManager` implementing the same interface as `BleManager` (to be implemented when the architecture stabilises)
- Testing with real BLE hardware remains manual, on a physical device

### CI

Dedicated workflow `.github/workflows/android-ci.yml` — separate from the Python one, triggered only when files in `android-app/` change:

```
git push  →  changes android-app/  →  android-ci.yml runs testDebugUnitTest + lintDebug
git push  →  changes backend_rpi4/ →  ci.yml runs pytest
```

## How to Add Tests

### 1. Test dependencies (`app/build.gradle.kts`)

Add inside `dependencies {}` (the two `testImplementation` lines are the new ones — the others are already present):

```kotlin
dependencies {
    // ... existing dependencies ...
    testImplementation(libs.junit)

    // MockWebServer to test the HTTP client without a real server
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")

    // Coroutines test to test suspend functions
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
}
```

### 2. Create the test files

Place them exactly at these paths (create directories if they don't exist):

```
android-app/app/src/test/java/com/myne/alg_calc/ble/BlePacketParserTest.kt
android-app/app/src/test/java/com/myne/alg_calc/network/ApiServiceTest.kt
```

The content of both is in the downloadable files — see the "Automated Tests" section in the repo.

### 3. Run the tests

```bash
cd android-app

# All unit tests
./gradlew testDebugUnitTest

# Single file only
./gradlew testDebugUnitTest --tests "com.myne.alg_calc.ble.BlePacketParserTest"

# Lint
./gradlew lintDebug
```

In Android Studio: right-click a test file → "Run".

HTML results are in:
`app/build/reports/tests/testDebugUnitTest/index.html`