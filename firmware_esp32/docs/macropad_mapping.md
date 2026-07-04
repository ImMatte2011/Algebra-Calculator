# BLE Macropad Mapping — MINI-KEYBOARD

Definitive reference for configuring the macropad in the manufacturer's EXE tool. Confirmed MAC: `E0:0F:7A:C3:C9:DF`.

Mapping obtained and verified with `scripts/hid_mapper.py` on real hardware (see that file for how to re-run the scan if the macropad is reconfigured).

## Layer 1 — Numbers and Basic Operators

| Physical key | Map to |
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
| 13 | `x` (letter) |
| 14 | `0` (numpad) |
| 15 | `ENTER` (numpad) |
| 16 | `/` (numpad) |

## Layer 2 — Symbols and Equations

| Physical key | Map to | Notes |
|---|---|---|
| 1 | **F17** | Square root — see below, replaces the old "sqrt" text macro |
| 2 | `Shift+6` | `^` (exponent) |
| 3 | `Shift+9` | `(` |
| 4 | `Shift+0` | `)` |
| 5 | `Shift+,` | `<` |
| 6 | `Shift+.` | `>` |
| 7 | Macro: `Shift+,` then `=` | `<=` |
| 8 | Macro: `Shift+.` then `=` | `>=` |
| 9 | Macro: `Shift+1` then `=` | `!=` |
| 10 | `=` | |
| 11 | *(free)* | |
| 12 | *(free)* | |
| 13 | `LEFT` | left arrow |
| 14 | `RIGHT` | right arrow |
| 15 | `UP` | up arrow |
| 16 | `DOWN` | down arrow |

**Note on F17**: previously key 1 sent the text macro `sqrt` (4 key presses: s-q-r-t). It has been replaced with a single F17 keycode for cleanliness — the firmware intercepts it and inserts `sqrt(` into the expression, leaving the cursor inside the parentheses for writing the argument (e.g. `sqrt(x^2+1)`).

**Note on `<=`, `>=`, `!=` macros**: these remain 2-key hardware macros (the macropad sends two separate HID events). The firmware needs no special handling: the two characters arrive in sequence and concatenate normally in the expression, exactly as if typed one at a time.

## Layer 3 — Direct Mathematical Actions

| Physical key | Keycode | Action |
|---|---|---|
| 1 | F1 | Simplify (`simplify`) |
| 2 | F2 | Expand (`expand`) |
| 3 | F3 | Factor (`factor`) |
| 4 | F4 | Type: equation |
| 5 | F5 | Type: inequality |
| 6 | F6 | Type: expression (opens the action sub-menu) |
| 7-16 | F7-F16 | *(free for future expansion)* |

Pressing one of these keys prepares the packet and sends it directly, without going through the interactive menu (which remains available only for matrix keypad users).

## Rotary Knobs (×3)

The knobs send **standard** HID keycodes, already handled by the firmware without dedicated logic:

| Knob | CCW | Click | CW |
|---|---|---|---|
| 1 | `LEFT` | `DELETE` | `RIGHT` |
| 2 | `UP` | `BACKSPACE` | `DOWN` |
| 3 | *(free)* | `ESC` (→ CLEAR) | *(free)* |

## Mathematical Symbols on the OLED Display

`sqrt(`, `<=`, `>=`, `!=` are saved and sent to the backend as plain text — the SymPy parser accepts them as-is, no server-side conversion needed.

On the OLED display, `drivers/oled_glyphs.py` replaces these substrings with dedicated 8×8 bitmaps (√, ≤, ≥, ≠) at the rendering level only — the underlying data in the expression never changes. To use them, call `display.show_expr_and_status_glyphs(...)` instead of the text version in `main.py`. See `firmware_esp32/drivers/oled_display_GLYPH_ADDON.py` for the code to integrate.

On the LCD display (matrix keypad variant), symbols remain plain ASCII text (`<=`, `>=`, `!=`, `sqrt(`) — the character LCD does not support custom bitmaps without using the CGRAM registers, which is out of scope for now.

## How to Remap if the Macropad is Reset

1. Connect the macropad to the PC, open the manufacturer's EXE tool.
2. Follow the table above layer by layer.
3. Verify with `python scripts/hid_mapper.py` (requires `mpremote`):
   ```bash
   mpremote cp scripts/hid_mapper.py :main.py
   mpremote run main.py
   ```
4. Press each key and compare the output with this document.