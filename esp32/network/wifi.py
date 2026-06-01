import network
import urequests
import ujson
import time
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv may not be available on MicroPython devices; skip if missing
    pass

SSID = os.getenv("WIFI_SSID")
PASS = os.getenv("WIFI_PASSWORD")
URL = os.getenv("API_URL")
TOKEN = os.getenv("API_TOKEN")

# WIFI
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)

while not wlan.isconnected():
    time.sleep(0.5)

print("WiFi OK", wlan.ifconfig())

# REQUEST
payload = {
    "expr": "integrate(x^2)"  # <-- modifica x input dinamico da KeyPad
}

headers = {
    "Authorization": "Bearer " + TOKEN
}

r = urequests.post(URL, json=payload, headers=headers)

print(r.text)
r.close()