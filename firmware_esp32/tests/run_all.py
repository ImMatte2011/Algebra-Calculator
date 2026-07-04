"""
run_all.py — Runs the pure logic tests (no hardware required).

Hardware tests (oled, ble_hid, ble_bridge) should be run individually.

Usage on ESP32:
    mpremote cp -r firmware_esp32/tests :tests
    mpremote run tests/run_all.py

Usage on PC (from the repo root or from firmware_esp32/):
    python firmware_esp32/tests/run_all.py
"""
import sys, os

# Firmware root path (parent of tests/)
if sys.implementation.name == "micropython":
    _tests_dir = "/tests"
else:
    from pathlib import Path
    _tests_dir = str(Path(__file__).parent)

LOGIC_TESTS = [
    "test_config.py",
    "test_glyphs.py",
    "test_input_handler.py",
    "test_display_scroller.py",
    "test_oled.py",
    "test_ble_bridge.py",
    "test_ble_hid.py",
]

total_pass = 0
total_fail = 0

for fname in LOGIC_TESTS:
    fpath = _tests_dir + "/" + fname
    print(f"\n{'='*44}")
    print(f"  {fname}")
    print('='*44)

    try:
        with open(fpath) as f:
            code = f.read()
        # Run in an isolated namespace; the tests define _pass and _fail as globals
        ns = {"__name__": "__main__", "__file__": fpath}
        try:
            exec(compile(code, fpath, "exec"), ns)
        except SystemExit as e:
            pass  # sys.exit(0) or sys.exit(1) — already printed by the test

        p  = ns.get("_pass", 0)
        f_ = ns.get("_fail", 0)
        total_pass += p
        total_fail += f_

    except Exception as e:
        import sys
        print(f"  ERROR running {fname}:")
        if sys.implementation.name == "micropython":
            sys.print_exception(e)
        else:
            import traceback
            traceback.print_exc()
        total_fail += 1

print(f"\n{'='*44}")
print(f"  TOTAL: {total_pass} passed, {total_fail} failed")
print('='*44)
sys.exit(0 if total_fail == 0 else 1)
