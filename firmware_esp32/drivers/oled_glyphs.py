"""
oled_glyphs.py — Bitmap 8x8 per simboli matematici non presenti nel font
ASCII built-in di framebuf (sqrt, <=, >=, !=).

Questi bitmap sono usati SOLO per il rendering sull'OLED — l'espressione
salvata in InputHandler resta sempre testo puro ("sqrt(", "<=", ">=", "!=").
Nessun altro file deve essere modificato per aggiungere/cambiare un glifo:
basta editare GLYPHS qui sotto.

Formato: ogni glifo è una lista di 8 byte, un byte per riga, bit più
significativo = pixel più a sinistra (MSB-first, come framebuf.MONO_VLSB
letto riga per riga). Per generare nuovi bitmap si possono usare tool web
tipo "8x8 LED matrix bitmap generator" e incollare l'output qui.

Pattern: la chiave è la sottostringa esatta da sostituire nel testo quando
viene visualizzata. L'ordine di match è quello di inserimento del dict,
quindi le sottostringhe più lunghe vanno messe per prime (es. "sqrt("
prima di eventuali pattern più corti che potrebbero sovrapporsi).
"""

# Radice quadrata (√) — tratto ascendente + vinculum orizzontale
_SQRT = bytes([
    0b00000011,
    0b00000110,
    0b00001100,
    0b01011000,
    0b01110000,
    0b00100000,
    0b00000000,
    0b00000000,
])

# Minore o uguale (≤)
_LE = bytes([
    0b00000010,
    0b00000100,
    0b00001000,
    0b00010000,
    0b00001000,
    0b00000100,
    0b00000010,
    0b01111110,
])

# Maggiore o uguale (≥)
_GE = bytes([
    0b01000000,
    0b00100000,
    0b00010000,
    0b00001000,
    0b00010000,
    0b00100000,
    0b01000000,
    0b01111110,
])

# Diverso (≠)
_NE = bytes([
    0b00010000,
    0b00010000,
    0b01111110,
    0b00010000,
    0b00010000,
    0b01111110,
    0b00010000,
    0b00010000,
])

# Mappa: sottostringa nel testo → bitmap 8x8.
# "sqrt(" è 5 caratteri ma occupa UN solo glifo (8px) sul display —
# risparmia spazio utile su un OLED 128px di larghezza.
GLYPHS = {
    "sqrt(": _SQRT,
    "<=":    _LE,
    ">=":    _GE,
    "!=":    _NE,
}

GLYPH_WIDTH  = 8
GLYPH_HEIGHT = 8


def split_with_glyphs(text):
    """
    Divide `text` in una lista di segmenti (str, "char") o (bytes, "glyph"),
    nell'ordine in cui appaiono. Usata da OledDisplay per il rendering.

    Esempio:
        split_with_glyphs("x<=5")
        → [("x", "char"), (_LE, "glyph"), ("5", "char")]
    """
    segments = []
    i = 0
    n = len(text)
    patterns = list(GLYPHS.keys())

    while i < n:
        matched = False
        for pat in patterns:
            if text.startswith(pat, i):
                segments.append((GLYPHS[pat], "glyph"))
                i += len(pat)
                matched = True
                break
        if not matched:
            segments.append((text[i], "char"))
            i += 1

    return segments