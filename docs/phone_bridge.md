# Phone Bridge Architecture

## Ruolo del telefono Android
Il telefono agisce da ponte tra l`ESP32` e il `Raspberry Pi`.

- `ESP32` invia l`input dell`utente via BLE.
- Il telefono riceve il BLE e inoltra la richiesta al `RPi` via HTTPS/LTE.
- Il `RPi` risponde con il risultato.
- Il telefono manda il risultato all`ESP32` via BLE o lo mostra localmente.

## Modalità di implementazione

### Fase 1: prototipo Termux/Python
- Eseguire uno script Python su Android con Termux.
- Ricevere BLE con libreria `bleak` (o libreria nativa Android se si evolve in app).
- Inviare POST a `https://<server>/solve` con `Authorization: Bearer <token>`.

### Fase 2: app Android
- Implementare il bridge come app che legge BLE e invia HTTPS.
- Gestire connessioni brevi e retry.

## Dettagli di sicurezza
- Usare sempre HTTPS per la comunicazione verso il RPi.
- Usare un token Bearer lungo e segreto.
- Se possibile, ricavare `token` da un file di configurazione sicuro sul telefono.
