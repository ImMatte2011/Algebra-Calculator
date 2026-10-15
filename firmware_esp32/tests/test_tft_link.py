"""Hardware-free tests for UART framing and the remote display input proxy."""
import sys

if sys.implementation.name == "micropython":
    sys.path.insert(0, "/")
else:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import ujson as json
except ImportError:
    import json
from drivers.tft_link import TftUartLink
from drivers.tft_remote_display import RemoteTftDisplay, RemoteTouchKeypadMux


class FakeUart:
    def __init__(self):
        self.incoming = bytearray()
        self.writes = []

    def read(self):
        if not self.incoming:
            return None
        data = bytes(self.incoming)
        self.incoming.clear()
        return data

    def write(self, data):
        self.writes.append(data)
        return len(data)


class FakeKeypad:
    def update(self):
        return "local-key"

    def reset_shift(self):
        self.was_reset = True


_pass = 0
_fail = 0


def check(name, condition):
    global _pass, _fail
    if condition:
        print("  PASS ", name)
        _pass += 1
    else:
        print("  FAIL ", name)
        _fail += 1


print("\n=== test_tft_link ===")
uart = FakeUart()
link = TftUartLink(uart)
link.send({"t": "s", "v": "line\nbreak", "l": 1})
check("send uses a newline-framed JSON message",
      uart.writes == [b'{"t":"s","v":"line\\nbreak","l":1}\n'])

uart.incoming.extend(b'{"t":"k","v":["ENTER"]}\n{"t":"k",')
check("receive parses complete frame", link.receive() == {"t": "k", "v": ["ENTER"]})
check("receive waits for the rest of a partial frame", link.receive() is None)
uart.incoming.extend(b'"v":["LEFT"]}\n')
check("receive resumes a partial frame",
      link.receive() == {"t": "k", "v": ["LEFT"]})

uart.incoming.extend(b"not-json\n")
uart.incoming.extend(b'{"t":"k","v":["RIGHT"]}\n')
check("invalid frame does not block the next valid frame",
      link.receive() == {"t": "k", "v": ["RIGHT"]})

try:
    link.send({"t": "r", "e": "x" * 1100})
    oversized_rejected = False
except ValueError:
    oversized_rejected = True
check("oversized outgoing frame is rejected", oversized_rejected)

uart = FakeUart()
link = TftUartLink(uart)
display = RemoteTftDisplay(link)
display.render("x^2", 2, status="ready", result="R" * 200)
rendered = json.loads(uart.writes[-1].decode())
check("remote display reports landscape dimensions",
      (display.width, display.height) == (480, 320))
check("render sends UI state rather than pixels",
      rendered["t"] == "r" and rendered["e"] == "x^2")
check("render limits result to visible TFT lines",
      len(rendered["v"]) == 162)

uart.incoming.extend(b'{"t":"k","v":["2","ENTER"]}\n')
keypad = FakeKeypad()
mux = RemoteTouchKeypadMux(keypad, link)
check("touch input delivers its first key", mux.update() == "2")
check("touch input queues the rest of a key batch", mux.update() == "ENTER")
check("local keypad remains available", mux.update() == "local-key")

print("\n  {} passed, {} failed".format(_pass, _fail))
sys.exit(0 if _fail == 0 else 1)
