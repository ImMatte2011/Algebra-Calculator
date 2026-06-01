from machine import Pin
import time

rows = [
    Pin(16, Pin.OUT),
    Pin(17, Pin.OUT),
    Pin(18, Pin.OUT),
    Pin(19, Pin.OUT),
]

cols = [
    Pin(21, Pin.IN, Pin.PULL_UP),
    Pin(22, Pin.IN, Pin.PULL_UP),
    Pin(23, Pin.IN, Pin.PULL_UP),
    Pin(25, Pin.IN, Pin.PULL_UP),
]

KEYS = [
    ["1","2","3","A"],
    ["4","5","6","B"],
    ["7","8","9","C"],
    ["*","0","#","D"]
]

for row in rows:
    row.value(0)

def scan_keypad():
    for r in range(4):
        rows[r].value(0)
        time.sleep_ms(2)
        for c in range(4):
            if cols[c].value() == 0:
                time.sleep_ms(100)
                if cols[c].value() == 0:
                    while cols[c].value() == 0:
                        time.sleep_ms(10)
                    rows[r].value(1)
                    return KEYS[r][c]
        rows[r].value(1)
    return None
