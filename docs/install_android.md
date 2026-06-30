# Installare l'app Android — dal repo al telefono

Questa guida copre il percorso completo: clonare il repo, compilare l'app
in Android Studio, e installarla su un telefono fisico (non emulatore,
necessario per il BLE).

## Prerequisiti

- [Android Studio](https://developer.android.com/studio) (Hedgehog o più recente)
- Un telefono Android con **Bluetooth Low Energy** (praticamente tutti
  dal 2014 in poi) e **Android 8.0 (API 26)** o superiore
- Cavo USB per collegare il telefono al PC, oppure debug wireless (ADB over Wi-Fi)
- Git installato

## 1. Clona il repository

```bash
git clone https://github.com/<utente>/Algebra-Calculator.git
cd Algebra-Calculator
```

L'app Android è nella sottocartella `android-app/` — è un progetto
Gradle indipendente, non serve toccare il resto del repo per compilarla.

## 2. Apri il progetto in Android Studio

`File → Open` e seleziona la cartella `android-app/` (non la root del
repo — Android Studio si aspetta `build.gradle.kts` nella cartella aperta).

Al primo avvio, Android Studio:
- crea automaticamente `local.properties` con il percorso del tuo SDK
  (non serve farlo a mano — vedi `local.properties.example` se vuoi
  capire cosa contiene)
- scarica le dipendenze Gradle (Retrofit, Compose, ecc.) — richiede
  connessione internet la prima volta

Se richiesto, lascia che Android Studio aggiorni il Gradle Wrapper alla
versione del progetto.

## 3. Abilita il debug USB sul telefono

Sul telefono:
1. `Impostazioni → Info telefono` → tocca 7 volte su "Numero build" per
   abilitare le Opzioni sviluppatore
2. `Impostazioni → Opzioni sviluppatore` → attiva **Debug USB**
3. Collega il telefono al PC via USB — comparirà un popup "Consenti
   debug USB?" sul telefono: conferma

Verifica che il telefono sia visto correttamente:
```bash
adb devices
```
Deve comparire il tuo dispositivo con stato `device` (non `unauthorized`).

## 4. Compila e installa

In Android Studio, con il telefono collegato e selezionato nella barra
in alto (accanto al pulsante ▶️ Run):

- Premi **Run ▶️** (o `Shift+F10`)

Questo compila l'APK in debug e lo installa automaticamente sul telefono.
La prima compilazione può richiedere qualche minuto.

In alternativa da terminale:
```bash
cd android-app
./gradlew installDebug
```

## 5. Configura l'app al primo avvio

L'app non ha valori preimpostati (vedi [android_app.md](android_app.md)
— nessun MAC o URL hardcoded nel sorgente). Alla prima apertura:

1. Vai nella schermata impostazioni dell'app
2. Inserisci l'**indirizzo MAC dell'ESP32** (visibile via `nRF Connect`
   o app simile, oppure lo trovi nei log seriali del firmware all'avvio)
3. Inserisci l'**URL del server FastAPI**, con porta:
   - se usi Tailscale: `http://100.x.x.x:8000/`
   - se usi Caddy/dominio pubblico: `https://tuo-dominio.duckdns.org/`
4. Se il backend gira con `ACCESS_MODE=public` (vedi
   [deploy.md](deploy.md)), inserisci anche il **token API** — deve
   coincidere con `API_TOKEN` nel `.env` del Raspberry Pi
5. Se usi `ACCESS_MODE=tailscale`, lascia il campo token vuoto

## 6. Concedi i permessi Bluetooth

Al primo tentativo di connessione, Android chiederà i permessi BLE:
- Android 12+: "Consenti a Calc Algebraica di trovare dispositivi nelle
  vicinanze?" → consenti
- Android < 12: chiederà il permesso di posizione (richiesto dal sistema
  per lo scan BLE su versioni precedenti, anche se l'app non usa la
  posizione — vedi [android_app.md](android_app.md#permessi-bluetooth))

## 7. Genera un APK da condividere (opzionale)

Se vuoi installare l'app su un telefono senza passare da Android Studio
ogni volta:

```bash
cd android-app
./gradlew assembleDebug
```

L'APK risultante è in `android-app/app/build/outputs/apk/debug/app-debug.apk`.
Trasferiscilo sul telefono (es. via cavo, email, o `adb install`) e
installalo manualmente — dovrai abilitare "Installa da fonti sconosciute"
per l'app che usi per aprirlo.

```bash
adb install android-app/app/build/outputs/apk/debug/app-debug.apk
```

## Problemi comuni

**"Device not found" / `adb devices` mostra `unauthorized`**
Scollega e ricollega il cavo USB, conferma di nuovo il popup sul telefono.

**L'app non trova l'ESP32 via BLE**
Verifica che il firmware ESP32 sia effettivamente acceso e in modalità
discoverable (controlla i log seriali). Verifica che il MAC inserito
nell'app corrisponda esattamente a quello dell'ESP32 — maiuscole/minuscole
sbagliate non si connettono.

**Errore 401 dal server**
Il token nell'app non coincide con `API_TOKEN` nel `.env` del backend,
oppure il backend è in modalità `public` e hai lasciato il token vuoto
nell'app.

**Errore di connessione di rete (timeout)**
Verifica che il telefono sia sulla stessa rete Tailscale del Raspberry
Pi (se usi quella modalità), o che l'URL/porta nel backend sia
raggiungibile dal telefono (prova ad aprire l'URL da un browser sul
telefono stesso).