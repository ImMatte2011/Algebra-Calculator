# Network Architecture

The ESP32 does not call the Raspberry Pi directly over WiFi. The fixed local
link is:

```text
ESP32 keypad/display
        |
        | BLE GATT
        v
Android app
        |
        | HTTP/HTTPS, depending on app settings and ACCESS_MODE
        v
Raspberry Pi 4 FastAPI backend
        |
        v
SymPy math engine
```

The Android app is the bridge. It receives the expression from the ESP32 over
BLE, sends it to the backend `/solve` endpoint, then sends the result back to
the ESP32 over BLE.

## Backend Access Modes

Backend exposure is selected in `.env` through `ACCESS_MODE`, which is read by
`backend_rpi4/config.py`.

| `ACCESS_MODE` | Android app URL | Token | Typical use |
|---|---|---|---|
| `public` | `https://your-domain.duckdns.org/` behind Caddy | Required | Access from the public internet |
| `tailscale` | `http://100.x.x.x:8000/` inside the tailnet | Not checked by the app | Private tailnet access |

In both modes, the ESP32 still talks only to the Android phone over BLE.

## Public Mode

Use this mode when the phone must reach the Raspberry Pi from outside the
local network without Tailscale.

```text
Android app
   |
 HTTPS + Authorization: Bearer <API_TOKEN>
   |
Caddy on :443
   |
reverse_proxy
   |
FastAPI on 127.0.0.1:8000
```

Recommended setup:

- expose only `443/tcp` to the internet;
- keep FastAPI bound to `127.0.0.1:8000`;
- use Caddy for automatic TLS certificates;
- use DuckDNS or another dynamic DNS provider if the home IP changes;
- set a strong `API_TOKEN`.

## Tailscale Mode

Use this mode when the phone and Raspberry Pi are in the same Tailscale
tailnet.

```text
Android app
   |
 Tailscale-encrypted HTTP
   |
FastAPI on the Pi tailnet address
```

In this mode Caddy, public TLS, DuckDNS, and the bearer token are not required
by the backend. The security perimeter is the tailnet itself.

## BLE Link

BLE is only the local ESP32 <-> Android link. It carries:

- expression packets from ESP32 to Android;
- result/error packets from Android to ESP32.

The ESP32 firmware may also use BLE as a central when `KEYPAD_TYPE="ble_hid"`
to read a BLE HID macropad, but that is separate from the Android bridge link.

## Backend API

The Android app calls:

```http
POST /solve
Authorization: Bearer <API_TOKEN>
```

Example request:

```json
{
  "expression": "x^2-1=0",
  "type": "equation",
  "action": null
}
```

Example response:

```json
{
  "ok": true,
  "result": "x = -1 or x = 1"
}
```

`GET /status` can be used as a health check.

## What To Avoid

- documenting ESP32 -> WiFi -> Raspberry Pi as the active architecture;
- exposing FastAPI directly to the public internet;
- using public HTTP without TLS;
- committing real tokens, IPs, domains, or WiFi credentials;
- using short or reused bearer tokens in `public` mode.
