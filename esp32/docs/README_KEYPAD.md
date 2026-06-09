# 🧮 Sistema a Doppio SHIFT - Calcolatrice Algebrica ESP32

Il tastierino matriciale 4x4 è stato potenziato introducendo **due modalità di SHIFT distinte** (Stato A e Stato B). Questo permette di mappare fino a 3 funzioni diverse su un singolo tasto fisico, risolvendo la mancanza di tasti per parentesi, incognite e operatori avanzati.

Il vecchio tasto fisso `K_SHIFT` è stato riciclato con la funzione **CMD_CLEAR** (Cancella tutto).

---

## 🧭 Indicatori di Stato sul Display LCD
La riga inferiore del display mostra lo stato corrente della tastiera nell'angolo in basso a destra:
* **Nessun indicatore**: Modalità Primaria (Numeri standard)
* **`[SH-A]`**: Shift A attivo (Operatori aritmetici, parentesi, incognita `x`)
* **`[SH-B]`**: Shift B attivo (Frecce di navigazione e operatori di confronto)

---

## 🗺️ Mappe dei Tasti (Keymaps)

### 1. Modalità Primaria (Default)
Attiva all'avvio. Fornisce la digitazione numerica standard e l'accesso alle modalità Shift.
* Preme `*` per passare a **SHIFT A**
* Preme `#` per passare a **SHIFT B**

| Tasto Fisico | Output / Azione | Descrizione |
| :--- | :--- | :--- |
| **`K_1`** fino a **`K_0`** | `1` o `0` | Cifre numeriche standard |
| **`K_STAR` (`*`)** | `CMD_SHIFT_A` | Attiva la modalità **SHIFT A** |
| **`K_POUND` (`#`)** | `CMD_SHIFT_B` | Attiva la modalità **SHIFT B** |
| **`K_SHIFT`** | `CMD_CLEAR` | Cancella interamente l'espressione |
| **`K_ENTER`** | `CMD_ENTER` | Apre il menu di invio/elaborazione |
| **`K_BACKSPACE`** | `CMD_BACKSPACE` | Cancella il carattere precedente |
| **`K_DELETE`** | `CMD_DELETE` | Cancella il carattere successivo |

---

### 🟢 2. Modalità SHIFT A (`*`)
Dedicata alla scrittura dell'espressione algebrica, alle parentesi e alla variabile incognita.

| Tasto Fisico | Mappatura | Funzione Speciale |
| :--- | :--- | :--- |
| **`K_1`** | **`(`** | Parentesi Tonda Aperta |
| **`K_2`** | **`)`** | Parentesi Tonda Chiusa |
| **`K_3`** | **`+`** | Somma |
| **`K_4`** | **`-`** | Sottrazione |
| **`K_5`** | **`*`** | Moltiplicazione |
| **`K_6`** | **`/`** | Divisione |
| **`K_7`** | **`^`** | Elevamento a Potenza |
| **`K_8`** | **`x`** | **Incognita Algebrica 'x'** |
| **`K_9`** | `9` | Fallback numerico |
| **`K_0`** | `0` | Fallback numerico |
| **`K_STAR`** | `CMD_SHIFT_A` | Disattiva lo Shift A (Torna a Primaria) |
| **`K_POUND`** | `CMD_SHIFT_B` | Salta direttamente a Shift B |

---

### 🔵 3. Modalità SHIFT B (`#`)
Dedicata alla navigazione del cursore (frecce) e ai simboli di confronto per equazioni/disequazioni.

| Tasto Fisico | Mappatura | Funzione Speciale |
| :--- | :--- | :--- |
| **`K_1`** | `CMD_LEFT` | **⬅️ Muove il cursore a sinistra** |
| **`K_2`** | `CMD_RIGHT` | **➡️ Muove il cursore a destra** |
| **`K_3`** | `CMD_UP` | ⬆️ Freccia Su (Menu) |
| **`K_4`** | `CMD_DOWN` | ⬇️ Freccia Giù (Menu) |
| **`K_5`** | **`>`** | Maggiore di |
| **`K_6`** | **`<`** | Minore di |
| **`K_7`** | **`>=`** | Maggiore o Uguale |
| **`K_8`** | **`<=`** | Minore o Uguale |
| **`K_9`** | **`!=`** | Diverso / Non Uguale |
| **`K_0`** | **`=`** | Uguale logico |
| **`K_STAR`** | `CMD_SHIFT_A` | Salta direttamente a Shift A |
| **`K_POUND`** | `CMD_SHIFT_B` | Disattiva lo Shift B (Torna a Primaria) |