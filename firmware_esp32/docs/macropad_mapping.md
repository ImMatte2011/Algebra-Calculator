# Mappatura Macropad BLE — MINI-KEYBOARD

Riferimento definitivo per la configurazione del macropad nel tool EXE del
produttore. MAC confermato: `E0:0F:7A:C3:C9:DF`.

Mappatura ottenuta e verificata con `scripts/hid_mapper.py` su hardware
reale (vedi quel file per come rieseguire la scansione se il macropad
viene riconfigurato).

## Layer 1 — Numeri e operatori base

| Tasto fisico | Da mappare a |
|---|---|
| 1 | `1` (numpad) |
| 2 | `2` (numpad) |
| 3 | `3` (numpad) |
| 4 | `+` (numpad) |
| 5 | `4` (numpad) |
| 6 | `5` (numpad) |
| 7 | `6` (numpad) |
| 8 | `-` (numpad) |
| 9 | `7` (numpad) |
| 10 | `8` (numpad) |
| 11 | `9` (numpad) |
| 12 | `*` (numpad) |
| 13 | `x` (lettera) |
| 14 | `0` (numpad) |
| 15 | `ENTER` (numpad) |
| 16 | `/` (numpad) |

## Layer 2 — Simboli ed equazioni

| Tasto fisico | Da mappare a | Note |
|---|---|---|
| 1 | **F17** | Radice — vedi sotto, sostituisce la vecchia macro testuale "sqrt" |
| 2 | `Shift+6` | `^` (esponente) |
| 3 | `Shift+9` | `(` |
| 4 | `Shift+0` | `)` |
| 5 | `Shift+,` | `<` |
| 6 | `Shift+.` | `>` |
| 7 | Macro: `Shift+,` poi `=` | `<=` |
| 8 | Macro: `Shift+.` poi `=` | `>=` |
| 9 | Macro: `Shift+1` poi `=` | `!=` |
| 10 | `=` | |
| 11 | *(libero)* | |
| 12 | *(libero)* | |
| 13 | `LEFT` | freccia sinistra |
| 14 | `RIGHT` | freccia destra |
| 15 | `UP` | freccia su |
| 16 | `DOWN` | freccia giù |

**Nota su F17**: in precedenza il tasto 1 mandava la macro testuale
`sqrt` (4 tasti: s-q-r-t). È stato sostituito con un singolo keycode F17
per pulizia — il firmware lo intercetta e inserisce `sqrt(` nell'espressione,
lasciando il cursore dentro le parentesi per scrivere l'argomento (es.
`sqrt(x^2+1)`).

**Nota sulle macro `<=`, `>=`, `!=`**: restano macro a 2 tasti a livello
hardware (il macropad manda due eventi HID separati). Il firmware non ha
bisogno di nessuna gestione speciale: i due caratteri arrivano in sequenza
e si concatenano normalmente nell'espressione, esattamente come se fossero
digitati uno alla volta.

## Layer 3 — Azioni matematiche dirette

| Tasto fisico | Keycode | Azione |
|---|---|---|
| 1 | F1 | Semplifica (`simplify`) |
| 2 | F2 | Espandi (`expand`) |
| 3 | F3 | Fattorizza (`factor`) |
| 4 | F4 | Tipo: equazione |
| 5 | F5 | Tipo: disequazione |
| 6 | F6 | Tipo: espressione (apre il sotto-menu azione) |
| 7-16 | F7-F16 | *(liberi per espansioni future)* |

Premendo uno di questi tasti, il pacchetto viene preparato e inviato
direttamente, senza passare dal menu interattivo (quello resta disponibile
solo per chi usa il tastierino matriciale).

## Knob rotativi (×3)

I knob mandano keycode HID **standard**, già gestiti dal firmware senza
bisogno di logica dedicata:

| Knob | CCW | Click | CW |
|---|---|---|---|
| 1 | `LEFT` | `DELETE` | `RIGHT` |
| 2 | `UP` | `BACKSPACE` | `DOWN` |
| 3 | *(libero)* | `ESC` (→ CLEAR) | *(libero)* |

## Simboli matematici sul display OLED

`sqrt(`, `<=`, `>=`, `!=` vengono salvati e inviati al backend come testo
puro — il parser SymPy li accetta così come sono, nessuna conversione
necessaria lato server.

Sul display OLED, `drivers/oled_glyphs.py` sostituisce queste sottostringhe
con bitmap 8×8 dedicati (√, ≤, ≥, ≠) solo a livello di rendering — il dato
sottostante nell'espressione non cambia mai. Per usarli, chiamare
`display.show_expr_and_status_glyphs(...)` invece della versione testuale
in `main.py`. Vedi `firmware_esp32/drivers/oled_display_GLYPH_ADDON.py`
per il codice da integrare.

Sul display LCD (variante matrix keypad), i simboli restano testo ASCII
puro (`<=`, `>=`, `!=`, `sqrt(`) — l'LCD a caratteri non supporta bitmap
custom senza usare i registri CGRAM, che è fuori scope per ora.

## Come ri-mappare se il macropad viene resettato

1. Collega il macropad al PC, apri il tool EXE del produttore.
2. Segui la tabella sopra layer per layer.
3. Verifica con `python scripts/hid_mapper.py` (richiede `mpremote`):
   ```bash
   mpremote cp scripts/hid_mapper.py :main.py
   mpremote run main.py
   ```
4. Premi ogni tasto e confronta l'output con questo documento.