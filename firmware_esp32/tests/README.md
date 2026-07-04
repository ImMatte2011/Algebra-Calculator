# firmware_esp32/tests/

Test del firmware ESP32. Divisi in due categorie:

## Test logici — nessun hardware richiesto

Testano logica pura (parsing, stato, scroller). Girano sia su ESP32 che
su PC con Python 3.

| File | Cosa testa |
|---|---|
| `test_config.py` | Struttura e validità di `config.py` |
| `test_glyphs.py` | `oled_glyphs.split_with_glyphs()` — segmentazione e bitmap |
| `test_input_handler.py` | `InputHandler` — editing, cursore, menu, azioni Layer 3, SQRT |
| `test_display_scroller.py` | `TextScroller` — finestra, scroll, edge cases |

**Esegui tutti in una volta:**

```bash
# su PC, dalla root del repo
python firmware_esp32/tests/run_all.py

# su ESP32
mpremote run firmware_esp32/tests/run_all.py
```

**Singolo test:**

```bash
python firmware_esp32/tests/test_input_handler.py
mpremote run firmware_esp32/tests/test_config.py
```

---

## Test hardware — richiedono dispositivi fisici

| File | Hardware richiesto | Cosa testa |
|---|---|---|
| `test_oled.py` | ESP32 + display OLED | Init, testo, glifi, invert — test visivi |
| `test_ble_hid.py` | ESP32 + macropad BLE | Connessione GATT, ricezione keycode |
| `test_ble_bridge.py` | ESP32 + telefono Android | BLEBridge peripheral, send/receive |

**Workflow consigliato — testa per gradi:**

```
1. test_config        (PC, 0 hardware)
2. test_glyphs        (PC, 0 hardware)
3. test_input_handler (PC, 0 hardware)
4. test_oled          (ESP32 + OLED)
5. test_ble_hid       (ESP32 + macropad)
6. test_ble_bridge    (ESP32 + macropad + telefono)
```

Non andare al passo successivo se quello precedente fallisce.

**Caricare ed eseguire un test hardware:**

```bash
mpremote cp firmware_esp32/tests/test_oled.py :test_oled.py
mpremote run test_oled.py
```

Oppure in una sessione REPL interattiva:

```bash
mpremote repl
# poi Ctrl+C per interrompere main.py se è in esecuzione
# poi incolla il contenuto del file test nel REPL
```

---

## Note su MicroPython

- `run_all.py` usa `exec()` per eseguire i test nello stesso processo —
  funziona sia su ESP32 che su PC.
- I test hardware usano `time.sleep_ms()` (MicroPython); su PC questo
  è disponibile solo se esplicitamente mocked, quindi vanno eseguiti
  solo su ESP32.
- `_pending_result = [None]` in `main.py` è il pattern MicroPython
  standard per passare dati da una callback IRQ al loop principale:
  MicroPython è single-threaded e non ha `threading.Queue`.
- I test logici mockano `ubluetooth` e `machine` automaticamente quando
  non disponibili, senza bisogno di file aggiuntivi.

---

## Aggiungere un nuovo test

Crea `firmware_esp32/tests/test_mio_modulo.py` seguendo questo schema:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mio_modulo import MiaClasse

_pass = 0
_fail = 0

def check(name, condition, detail=""):
    global _pass, _fail
    if condition:
        print(f"  PASS  {name}")
        _pass += 1
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        _fail += 1

print("\n=== test_mio_modulo ===")

# ... i tuoi check ...

print(f"\n  {_pass} passed, {_fail} failed")
sys.exit(0 if _fail == 0 else 1)
```

Se è un test logico (no hardware), aggiungilo alla lista `LOGIC_TESTS`
in `run_all.py`.
