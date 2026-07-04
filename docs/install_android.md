# Installing the Android App — From Repo to Phone

This guide covers the full path: cloning the repo, building the app in Android Studio, and installing it on a physical phone (not an emulator — required for BLE).

## Prerequisites

- [Android Studio](https://developer.android.com/studio) (Hedgehog or newer)
- An Android phone with **Bluetooth Low Energy** (virtually all devices since 2014) and **Android 8.0 (API 26)** or higher
- A USB cable to connect the phone to the PC, or wireless debugging (ADB over Wi-Fi)
- Git installed

## 1. Clone the Repository

```bash
git clone https://github.com/<user>/Algebra-Calculator.git
cd Algebra-Calculator
```

The Android app is in the `android-app/` subfolder — it is an independent Gradle project; you don't need to touch the rest of the repo to build it.

## 2. Open the Project in Android Studio

`File → Open` and select the `android-app/` folder (not the repo root — Android Studio expects `build.gradle.kts` in the opened folder).

On first launch, Android Studio will:
- automatically create `local.properties` with your SDK path (no need to do it manually — see `local.properties.example` if you want to understand what it contains)
- download Gradle dependencies (Retrofit, Compose, etc.) — requires an internet connection on the first run

If prompted, let Android Studio update the Gradle Wrapper to the project version.

## 3. Enable USB Debugging on the Phone

On the phone:
1. `Settings → About phone` → tap "Build number" 7 times to enable Developer Options
2. `Settings → Developer options` → enable **USB Debugging**
3. Connect the phone to the PC via USB — an "Allow USB debugging?" popup will appear on the phone: confirm

Verify the phone is recognised correctly:
```bash
adb devices
```
Your device should appear with status `device` (not `unauthorized`).

## 4. Build and Install

In Android Studio, with the phone connected and selected in the toolbar (next to the ▶️ Run button):

- Press **Run ▶️** (or `Shift+F10`)

This compiles the debug APK and automatically installs it on the phone. The first build may take a few minutes.

Alternatively, from the terminal:
```bash
cd android-app
./gradlew installDebug
```

## 5. Configure the App on First Launch

The app has no preset values (see [android_app.md](android_app.md) — no MAC or URL hardcoded in the source). On first launch:

1. Go to the app's settings screen
2. Enter the **ESP32 MAC address** (visible via `nRF Connect` or a similar app, or find it in the firmware serial logs at startup)
3. Enter the **FastAPI server URL**, with port:
   - if using Tailscale: `http://100.x.x.x:8000/`
   - if using Caddy/public domain: `https://your-domain.duckdns.org/`
4. If the backend runs with `ACCESS_MODE=public` (see [deploy.md](deploy.md)), also enter the **API token** — it must match `API_TOKEN` in the Raspberry Pi's `.env`
5. If using `ACCESS_MODE=tailscale`, leave the token field empty

## 6. Grant Bluetooth Permissions

On the first connection attempt, Android will ask for BLE permissions:
- Android 12+: "Allow Calc Algebraica to find nearby devices?" → allow
- Android < 12: will ask for location permission (required by the system for BLE scanning on older versions, even though the app does not use location — see [android_app.md](android_app.md#bluetooth-permissions))

## 7. Generate a Shareable APK (Optional)

If you want to install the app on a phone without going through Android Studio every time:

```bash
cd android-app
./gradlew assembleDebug
```

The resulting APK is at `android-app/app/build/outputs/apk/debug/app-debug.apk`. Transfer it to the phone (e.g. via cable, email, or `adb install`) and install it manually — you will need to enable "Install from unknown sources" for the app you use to open it.

```bash
adb install android-app/app/build/outputs/apk/debug/app-debug.apk
```

## Common Issues

**"Device not found" / `adb devices` shows `unauthorized`**
Unplug and replug the USB cable, confirm the popup on the phone again.

**The app can't find the ESP32 via BLE**
Verify the ESP32 firmware is actually running and in discoverable mode (check the serial logs). Verify the MAC entered in the app matches the ESP32's MAC exactly — wrong capitalisation will prevent connection.

**401 error from the server**
The token in the app does not match `API_TOKEN` in the backend's `.env`, or the backend is in `public` mode and you left the token empty in the app.

**Network connection error (timeout)**
Verify the phone is on the same Tailscale network as the Raspberry Pi (if using that mode), or that the URL/port in the backend is reachable from the phone (try opening the URL in the phone's browser).