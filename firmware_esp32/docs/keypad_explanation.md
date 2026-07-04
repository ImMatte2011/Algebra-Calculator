# 🧮 Dual SHIFT System — ESP32 Algebraic Calculator

The 4x4 matrix keypad has been enhanced by introducing **two distinct SHIFT modes** (State A and State B). This allows up to 3 different functions to be mapped to a single physical key, solving the lack of keys for parentheses, unknowns and advanced operators.

The old fixed `K_SHIFT` key has been repurposed with the **CMD_CLEAR** function (clear all).

---

## 🧭 Status Indicators on the LCD Display
The bottom row of the display shows the current keyboard state in the bottom-right corner:
* **No indicator**: Primary mode (standard numbers)
* **`[SH-A]`**: Shift A active (arithmetic operators, parentheses, unknown variable `x`)
* **`[SH-B]`**: Shift B active (navigation arrows and comparison operators)

---

## 🗺️ Key Maps (Keymaps)

### 1. Primary Mode (Default)
Active at startup. Provides standard numeric input and access to Shift modes.
* Press `*` to switch to **SHIFT A**
* Press `#` to switch to **SHIFT B**

| Physical Key | Output / Action | Description |
| :--- | :--- | :--- |
| **`K_1`** to **`K_0`** | `1` to `0` | Standard numeric digits |
| **`K_STAR` (`*`)** | `CMD_SHIFT_A` | Activates **SHIFT A** mode |
| **`K_POUND` (`#`)** | `CMD_SHIFT_B` | Activates **SHIFT B** mode |
| **`K_SHIFT`** | `CMD_CLEAR` | Clears the entire expression |
| **`K_ENTER`** | `CMD_ENTER` | Opens the send/process menu |
| **`K_BACKSPACE`** | `CMD_BACKSPACE` | Deletes the previous character |
| **`K_DELETE`** | `CMD_DELETE` | Deletes the next character |

---

### 🟢 2. SHIFT A Mode (`*`)
Dedicated to writing algebraic expressions, parentheses and the unknown variable.

| Physical Key | Mapping | Special Function |
| :--- | :--- | :--- |
| **`K_1`** | **`(`** | Open Round Bracket |
| **`K_2`** | **`)`** | Close Round Bracket |
| **`K_3`** | **`+`** | Addition |
| **`K_4`** | **`-`** | Subtraction |
| **`K_5`** | **`*`** | Multiplication |
| **`K_6`** | **`/`** | Division |
| **`K_7`** | **`^`** | Exponentiation |
| **`K_8`** | **`x`** | **Algebraic Unknown 'x'** |
| **`K_9`** | `9` | Numeric fallback |
| **`K_0`** | `0` | Numeric fallback |
| **`K_STAR`** | `CMD_SHIFT_A` | Deactivates Shift A (returns to Primary) |
| **`K_POUND`** | `CMD_SHIFT_B` | Jumps directly to Shift B |

---

### 🔵 3. SHIFT B Mode (`#`)
Dedicated to cursor navigation (arrows) and comparison symbols for equations/inequalities.

| Physical Key | Mapping | Special Function |
| :--- | :--- | :--- |
| **`K_1`** | `CMD_LEFT` | **⬅️ Move cursor left** |
| **`K_2`** | `CMD_RIGHT` | **➡️ Move cursor right** |
| **`K_3`** | `CMD_UP` | ⬆️ Arrow Up (Menu) |
| **`K_4`** | `CMD_DOWN` | ⬇️ Arrow Down (Menu) |
| **`K_5`** | **`>`** | Greater than |
| **`K_6`** | **`<`** | Less than |
| **`K_7`** | **`>=`** | Greater than or equal |
| **`K_8`** | **`<=`** | Less than or equal |
| **`K_9`** | **`!=`** | Not equal |
| **`K_0`** | **`=`** | Logical equal |
| **`K_STAR`** | `CMD_SHIFT_A` | Jumps directly to Shift A |
| **`K_POUND`** | `CMD_SHIFT_B` | Deactivates Shift B (returns to Primary) |