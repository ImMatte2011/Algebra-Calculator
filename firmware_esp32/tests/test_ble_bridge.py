"""
test_ble_bridge.py — Tests BLEBridge (peripheral toward the phone).
Requires hardware + an Android phone with the app installed.

Sequence:
  1. Init BLEBridge → PASS/FAIL
  2. Start advertising
  3. Wait for a connection from the phone (configurable timeout)
  4. Once connected, send a test message
  5. Wait for a reply (payload sent by the phone)
  6. Report PASS/FAIL

Use the Android app in normal mode: open the app and make sure it tries to connect to the ESP32 during the test.

Usage:
    mpremote cp firmware_esp32/tests/test_ble_bridge.py :test_ble_bridge.py
    mpremote run test_ble_bridge.py
"""
import sys, time
sys.path.insert(0, "/")

CONN_TIMEOUT_S = 30
MSG_TIMEOUT_S  = 15
TEST_PACKET    = "('x^2-1', 'equation', None, None)"

_pass = 0
_fail = 0
_received = [None]

def check(name, condition, detail=""):
    global _pass, _fail
    if condition:
        print(f"  PASS  {name}")
        _pass += 1
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        _fail += 1

print("\n=== test_ble_bridge ===")

# Import
try:
    from config import CONFIG
    from ble.ble_bridge import BLEBridge
    check("import", True)
except Exception as e:
    check("import", False, str(e))
    sys.exit(1)

# Receive callback
def on_msg(msg):
    _received[0] = msg
    print(f"  RECEIVED FROM PHONE: {repr(msg[:80])}")

# Init
try:
    bridge = BLEBridge(callback_on_receive=on_msg)
    check("BLEBridge() without crashing", True)
except Exception as e:
    check("BLEBridge() without crashing", False, str(e))
    sys.exit(1)

# Advertising
print(f"\n  Starting advertising as '{CONFIG.get('BLE_NAME', 'CALC-ESP32')}'...")
try:
    bridge.start_advertising(force=True)
    check("start_advertising() without crashing", True)
except Exception as e:
    check("start_advertising()", False, str(e))
    sys.exit(1)

# Wait for connection
print(f"  Open the Android app and connect. Timeout: {CONN_TIMEOUT_S}s")
start = time.time()
while not bridge.is_connected():
    bridge.poll()
    if time.time() - start > CONN_TIMEOUT_S:
        check(f"phone connected within {CONN_TIMEOUT_S}s", False, "timeout")
        sys.exit(1)
    time.sleep_ms(100)

check(f"phone connected within {CONN_TIMEOUT_S}s", True)

# Send test packet
print(f"\n  Sending packet: {TEST_PACKET}")
try:
    bridge.send_result(TEST_PACKET)
    check("send_result() without crashing", True)
except Exception as e:
    check("send_result()", False, str(e))

# Wait for a reply (the phone should send the result back from the RPi)
print(f"  Waiting for a reply from the phone ({MSG_TIMEOUT_S}s)...")
print("  (The phone must call the RPi and send the result back)")
start = time.time()
while _received[0] is None:
    bridge.poll()
    if time.time() - start > MSG_TIMEOUT_S:
        break
    time.sleep_ms(100)

if _received[0] is not None:
    check("reply received from the phone", True)
    check("reply starts with 'result:' or 'error:'",
          _received[0].startswith("result:") or _received[0].startswith("error:"),
          f"got: {repr(_received[0][:40])}")
else:
    check("reply received within timeout",
          False, "timeout — verify that the Android app is open and the RPi is active")

print(f"\n  {_pass} passed, {_fail} failed")
