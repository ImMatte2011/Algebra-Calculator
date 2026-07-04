"""
test_glyphs.py — Tests oled_glyphs.split_with_glyphs() without hardware.
Works on both ESP32 and PC.

Usage:
    mpremote run firmware_esp32/tests/test_glyphs.py
    or:  python firmware_esp32/tests/test_glyphs.py
"""
import sys, os
if sys.implementation.name == "micropython":
    sys.path.insert(0, "/")
else:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from drivers.oled_glyphs import split_with_glyphs, GLYPHS, GLYPH_WIDTH
except Exception as e:
    print("FAIL import oled_glyphs:", e)
    sys.exit(1)

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

print("\n=== test_glyphs ===")

# GLYPHS dict must be non-empty and bitmaps must be correctly formatted
check("GLYPHS is not empty", len(GLYPHS) > 0)
for pat, bmp in GLYPHS.items():
    check(f"bitmap '{pat}' is 8 bytes", len(bmp) == 8,
          f"len={len(bmp)}")

# split_with_glyphs: plain text, no glyph
segs = split_with_glyphs("x+1")
check("plain text → 3 char segments", len(segs) == 3)
check("all segments are 'char'", all(k == "char" for _, k in segs))
check("chars are correct", [c for c, _ in segs] == ["x", "+", "1"])

# split_with_glyphs: sqrt
segs = split_with_glyphs("sqrt(x)")
kinds = [k for _, k in segs]
check("sqrt( → first segment is glyph", kinds[0] == "glyph")
check("sqrt( → remaining segments are char", all(k == "char" for k in kinds[1:]))
check("chars after the glyph are correct",
      [c for c, k in segs if k == "char"] == ["x", ")"])

# split_with_glyphs: <=
segs = split_with_glyphs("x<=5")
check("x<=5 → 3 segments", len(segs) == 3,
      f"got {len(segs)}")
check("<= recognized as glyph", segs[1][1] == "glyph")

# split_with_glyphs: >= and !=
for pat, expr, expected_chars in [
    (">=", "x>=0",  ["x", "0"]),
    ("!=", "x!=y",  ["x", "y"]),
]:
    segs = split_with_glyphs(expr)
    chars = [c for c, k in segs if k == "char"]
    check(f"{pat} recognized as glyph",
          any(k == "glyph" for _, k in segs))
    check(f"chars around {pat} are correct", chars == expected_chars,
          f"got {chars}")

# split_with_glyphs: complex expression
segs = split_with_glyphs("sqrt(x^2+1)<=0")
glyphs_found = [c for c, k in segs if k == "glyph"]
check("complex expression: 2 glyphs found", len(glyphs_found) == 2,
      f"found {len(glyphs_found)}")

# GLYPH_WIDTH
check("GLYPH_WIDTH == 8", GLYPH_WIDTH == 8)

print(f"\n  {_pass} passed, {_fail} failed")
sys.exit(0 if _fail == 0 else 1)
