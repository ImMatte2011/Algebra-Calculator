# TFT su una seconda ESP32

Il firmware supporta il display ST7796/XPT2046 collegato a una ESP32 distinta
dalla ESP32 che esegue la calcolatrice. La scheda principale invia aggiornamenti
UI compatti (testo, cursore, risultato e stato); la scheda display disegna
localmente i pixel e rimanda gli eventi touch. Non viene trasferito un framebuffer.

## Collegamento

Configurare lo stesso `TFT_LINK` in `config.py` per entrambe le schede, poi
collegare:

| ESP32 logica | ESP32 display |
|---|---|
| TX (`TX_PIN`) | RX (`RX_PIN`) |
| RX (`RX_PIN`) | TX (`TX_PIN`) |
| GND | GND |

La UART usa livelli logici ESP32 a 3,3 V: non collegare segnali RS-232 o 5 V.
I pin GPIO 16/17 e UART 2 sono i valori iniziali; modificarli se sono già usati
dalla propria scheda (in particolare su moduli con PSRAM). La SPI del TFT e del
touch rimane collegata solo alla scheda display.

## Avvio

1. Sulla ESP32 logica impostare `DISPLAY_TYPE` a `tft_remote`; mantenere qui la
   configurazione keypad/BLE abituale e caricare normalmente il firmware.
2. Sulla ESP32 display caricare i moduli `config.py`, `drivers/` e
   `tft_display_node.py`, poi eseguire `tft_display_node.py` come programma
   principale.
3. Abilitare `TOUCH.ENABLED` per rimandare i tasti touch alla scheda logica.
   Per un TFT senza touch impostarlo a `False`.

Le due schede usano il medesimo firmware/configurazione TFT e gli stessi
parametri UART. La ESP32 display non deve avviare `main.py`: esegue solo il
servizio `tft_display_node.py`, senza inizializzare BLE o la logica calcolatrice.

Test locale senza hardware: `python firmware_esp32/tests/test_tft_link.py`.
Il test visivo e la calibrazione touch richiedono invece la ESP32 display e
restano in `tests/test_tft.py`.
