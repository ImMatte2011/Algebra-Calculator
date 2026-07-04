"""
oled_glyphs.py — 8x8 bitmaps for mathematical symbols not present in the
built-in framebuf ASCII font (sqrt, <=, >=, !=).

These bitmaps are used ONLY for OLED rendering — the expression stored in
InputHandler remains plain text ("sqrt(", "<=", ">=", "!="). No other file
needs to be changed to add or update a glyph; just edit GLYPHS below.

Format: each glyph is a list of 8 bytes, one byte per row, with the most
significant bit as the leftmost pixel (MSB-first, like framebuf.MONO_VLSB
read row by row). To generate new bitmaps, you can use web tools such as the
"8x8 LED matrix bitmap generator" and paste the output here.

Pattern: the key is the exact substring to replace in the text when it is
rendered. Matching order follows dictionary insertion order, so longer
substrings should go first (for example, "sqrt(" before shorter patterns that
might overlap).
"""

# Square root (√) — ascending stroke + horizontal vinculum
_SQRT = bytes([
    0b00000011,
    0b00000100,
    0b00000100,
    0b10001000,
    0b01001000,
    0b01010000,
    0b00110000,
    0b00100000,
])

# Less than or equal (≤)
_LE = bytes([
    0b00000000,
    0b00000110,
    0b00011000,
    0b01100000,
    0b00011000,
    0b11000110,
    0b00110000,
    0b00001100,
])

# Greater than or equal (≥)
_GE = bytes([
    0b00000000,
    0b01100000,
    0b00011000,
    0b00000110,
    0b00011000,
    0b01100011,
    0b00001100,
    0b00110000,
])

# Not equal (≠)
_NE = bytes([
    0b00000010,
    0b00000100,
    0b01111110,
    0b00001000,
    0b00010000,
    0b01111110,
    0b00100000,
    0b01000000,
])

# Map: substring in text → 8x8 bitmap.
# "sqrt(" is 5 characters but occupies ONE glyph (8px) on the display —
# it saves useful space on a 128px-wide OLED.
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
    Splits `text` into a list of segments (str, "char") or (bytes, "glyph"),
    in the order they appear. Used by OledDisplay for rendering.

    Example:
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