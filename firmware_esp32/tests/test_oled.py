"""
test_oled.py — Visual test for the OLED display. Requires hardware.

Uses the configuration in config.py. It does not produce automatic PASS/FAIL
results for the visual tests (you need to look at the display), but it prints
PASS/FAIL for initialization and crash errors.

Sequence:
  1. Init display (automatic) → PASS/FAIL
  2. Clear + checkerboard pattern → look at the display
  3. Text on every available row
  4. Mathematical glyphs (√, ≤, ≥, ≠) if USE_GLYPHS=True
  5. Typical expression with glyphs
  6. Color inversion (invert) → the display appears inverted
  7. Finish: show "TEST DONE"

Usage:
    mpremote cp firmware_esp32/tests/test_oled.py :test_oled.py
    mpremote run test_oled.py
"""
import sys, os, time
sys.path.insert(0, "/")

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

def section(title):
    print(f"\n--- {title} ---")

print("\n=== test_oled ===")

# Import config
section("Import")
try:
    from config import CONFIG
    check("import config", True)
except Exception as e:
    check("import config", False, str(e))
    sys.exit(1)

check("DISPLAY_TYPE == oled",
      CONFIG.get("DISPLAY_TYPE") == "oled",
      f"it is '{CONFIG.get('DISPLAY_TYPE')}' — this test requires OLED")
if CONFIG.get("DISPLAY_TYPE") != "oled":
    sys.exit(1)

# Import and init display
section("Init display")
try:
    from drivers.oled_display import OledDisplay
    check("import OledDisplay", True)
except Exception as e:
    check("import OledDisplay", False, str(e))
    sys.exit(1)

try:
    display = OledDisplay()
    check("OledDisplay() without crashing", True)
except Exception as e:
    check("OledDisplay() without crashing", False, str(e))
    print("  Verify the SPI/I2C pins in config.py OLED")
    sys.exit(1)

# Test 1: clear
section("Clear")
try:
    display.clear()
    check("clear() without crashing", True)
    print("  VISUAL: display completely off")
    time.sleep_ms(800)
except Exception as e:
    check("clear() without crashing", False, str(e))

# Test 2: checkerboard pattern (alternating fill_rect)
section("Checkerboard pattern")
try:
    display._fb.fill(0)
    w, h = display.width, display.height
    cell = 8
    for row in range(h // cell):
        for col in range(w // cell):
            if (row + col) % 2 == 0:
                display._fb.fill_rect(col*cell, row*cell, cell, cell, 1)
    display.show()
    check("checkerboard pattern without crashing", True)
    print("  VISUAL: 8x8 pixel checkerboard")
    time.sleep_ms(1500)
except Exception as e:
    check("checkerboard pattern without crashing", False, str(e))

# Test 3: text on every row (8px font → 8 rows on 64px)
section("Text on every row")
try:
    display._fb.fill(0)
    n_rows = display.height // display.CHAR_H
    for i in range(n_rows):
        display.show_text(f"Row {i}: ABCDEF12", line=i)
    check(f"text on {n_rows} rows without crashing", True)
    print(f"  VISUAL: text on {n_rows} rows (Row 0 to Row {n_rows-1})")
    time.sleep_ms(2000)
except Exception as e:
    check("text on every row without crashing", False, str(e))

# Test 4: glifi matematici
use_glyphs = CONFIG["OLED"].get("USE_GLYPHS", True)
section(f"Mathematical glyphs (USE_GLYPHS={use_glyphs})")
if use_glyphs:
    try:
        from drivers.oled_glyphs import split_with_glyphs, GLYPHS
        check("import oled_glyphs", True)

        display._fb.fill(0)
        display.show_text_glyphs("sqrt(<= >= !=", line=0)
        print("  VISUAL: row 0 -> glyph 'sqrt()' then '<=' then space then '>=' then space then '!='")
        time.sleep_ms(2000)

        display._fb.fill(0)
        display.show_text_glyphs("x<=5", line=0)
        display.show_text_glyphs("y>=0", line=1)
        display.show_text_glyphs("a!=b", line=2)
        display.show_text_glyphs("sqrt(x^2)", line=3)
        print("  VISUAL: x<=5 | y>=0 | a!=b | sqrt(x^2)")
        time.sleep_ms(2500)
        check("glyph rendering without crashing", True)
    except Exception as e:
        check("rendering glifi", False, str(e))
else:
    print("  SKIP: USE_GLYPHS=False, plain text")
    display.show_text("sqrt(x^2)<=0", line=0)
    time.sleep_ms(1500)

# Test 5: show_expr_and_status (o versione glifi)
section("show_expr_and_status")
try:
    if use_glyphs:
        display.show_expr_and_status_glyphs("sqrt(x^2-1)<=0", "BLE:OK")
    else:
        display.show_expr_and_status("sqrt(x^2-1)<=0", "BLE:OK")
    check("show_expr_and_status without crashing", True)
    print("  VISUAL: expression at the top, 'BLE:OK' at the bottom")
    time.sleep_ms(2000)
except Exception as e:
    check("show_expr_and_status", False, str(e))

# Test 6: invert e set_contrast
section("Invert and contrast")
try:
    display.invert(True)
    print("  VISUAL: display inverted (white background)")
    time.sleep_ms(800)
    display.invert(False)
    print("  VISUAL: normal display")
    time.sleep_ms(400)
    display.set_contrast(0)
    print("  VISUAL: minimum brightness")
    time.sleep_ms(400)
    display.set_contrast(0xCF)
    print("  VISUAL: normal brightness")
    check("invert and contrast without crashing", True)
except Exception as e:
    check("invert and contrast", False, str(e))

# End
section("End")
display._fb.fill(0)
display.show_text("TEST DONE", line=0)
display.show_text(f"{_pass}ok {_fail}fail", line=1)
display.show()

print(f"\n  {_pass} passed, {_fail} failed")
print("  Check the display for the visual tests.")
