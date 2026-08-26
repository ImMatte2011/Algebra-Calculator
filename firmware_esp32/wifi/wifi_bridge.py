"""
wifi_bridge.py — Async WiFi bridge. Drop-in per BLEBridge.

SOLVE_MODE:
  "direct"  → HTTP diretto al RPi (WiFi richiesto)
  "phone"   → delega sempre al bridge BLE (phone come proxy)
  "auto"    → ping RPi all'avvio; se raggiungibile usa direct,
               altrimenti delega a BLE; ricontrolla ogni RECHECK_S

main.py deve chiamare asyncio.run(app.run_async()) se bridge.async_mode=True.
"""

import network
import uasyncio
import ujson
import time
from config import CONFIG
from utils import logger

_CFG = CONFIG.get("WIFI", {})


def _rpi_host_port():
    url = _CFG.get("RPI_URL", "http://192.168.1.100:8000")
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    hostport = url.split("/")[0]
    if ":" in hostport:
        h, p = hostport.rsplit(":", 1)
        return h, int(p)
    return hostport, 80


class WiFiBridge:
    async_mode = True          # flag rilevato da main.py

    def __init__(self, callback=None, ble_fallback=None):
        self.callback    = callback
        self._ble        = ble_fallback    # BLEBridge per fallback phone/auto
        self._solve_mode = _CFG.get("SOLVE_MODE", "auto")
        self._rx_queue   = []              # risultati → CalculatorApp
        self._tx_queue   = []              # pacchetti da inviare
        self._ble_queue  = []              # pacchetti da delegare a BLE (main.py legge)
        self._wlan       = None
        self._use_direct = (self._solve_mode == "direct")
        self._last_check = 0

        # Intercetta risultati BLE (fallback)
        if self._ble is not None:
            self._ble.callback = self._on_ble_result

    def _on_ble_result(self, msg):
        self._rx_queue.append(msg)

    # ---------------------------------------------------------------
    # Interfaccia BLEBridge-compatibile
    # ---------------------------------------------------------------

    def start_advertising(self, force=False):
        """In direct mode no-op; in phone/auto avvia advertising BLE se disponibile."""
        if self._ble is not None and not self._use_direct:
            self._ble.start_advertising(force=force)

    def is_connected(self):
        if self._solve_mode == "phone":
            return self._ble is not None and self._ble.is_connected()
        return self._wifi_ok()   # direct/auto: connesso se WiFi up

    def poll(self):
        """Consegna messaggi al callback di CalculatorApp."""
        if self._ble is not None and not self._use_direct:
            self._ble.poll()
        while self._rx_queue:
            msg = self._rx_queue.pop(0)
            if self.callback:
                try:
                    self.callback(msg)
                except Exception as e:
                    logger.warning("WiFiBridge: callback error: %s", e)

    def send_result(self, packet_str):
        """Non-bloccante: accoda per il background task."""
        self._tx_queue.append(packet_str)

    def check_connection(self):
        return self.is_connected()

    # ---------------------------------------------------------------
    # Background task asyncio
    # ---------------------------------------------------------------

    async def run_background(self):
        if self._solve_mode != "phone":
            await self._wifi_connect_async()

        if self._solve_mode == "auto":
            self._use_direct = await self._ping_rpi()
            self._last_check = time.time()
            logger.info("WiFiBridge auto: direct=%s", self._use_direct)
            if not self._use_direct and self._ble is not None:
                # matrix: avvia advertising subito
                if CONFIG.get("KEYPAD_TYPE") != "ble_hid":
                    self._ble.start_advertising(force=True)
                # ble_hid: main.py gestisce via mode_manager quando serve

        while True:
            # Riconnetti WiFi se perso
            if not self._wifi_ok() and self._solve_mode != "phone":
                await self._wifi_connect_async()

            # Ricontrolla direct in auto mode
            if (self._solve_mode == "auto"
                    and not self._use_direct
                    and time.time() - self._last_check >= _CFG.get("RECHECK_S", 60)):
                if await self._ping_rpi():
                    self._use_direct = True
                    logger.info("WiFiBridge: RPi online, ripristino direct")
                self._last_check = time.time()

            # Processa coda uscita
            if self._tx_queue:
                packet = self._tx_queue.pop(0)
                await self._dispatch(packet)

            if self._tx_phone_queue:
                packet = self._tx_phone_queue.pop(0)
                result = await self._send_phone(packet)
                self._rx_queue.append(result)

            await uasyncio.sleep_ms(50)

    async def _dispatch(self, packet):
        if self._solve_mode == "phone":
            self._delegate_phone(packet)
            return

        if self._use_direct:
            result = await self._send_direct(packet)
            if result.startswith("error:") and self._solve_mode == "auto" and not self._use_direct:
                logger.info("WiFiBridge: direct fallito, delego a phone")
                self._delegate_phone(packet)
            else:
                self._rx_queue.append(result)
        else:
            self._delegate_phone(packet)

    def _delegate_phone(self, packet):
        """Fallback: chiama il server HTTP sul telefono invece del BLE bridge."""
        self._tx_phone_queue.append(packet)

    # ---------------------------------------------------------------
    # WiFi
    # ---------------------------------------------------------------

    def _wifi_ok(self):
        return self._wlan is not None and self._wlan.isconnected()

    async def _wifi_connect_async(self):
        ssid = _CFG.get("SSID", "")
        if not ssid:
            logger.error("WiFiBridge: WIFI.SSID non configurato")
            return
        try:
            self._wlan = network.WLAN(network.STA_IF)
            self._wlan.active(True)
            if self._wlan.isconnected():
                return
            logger.info("WiFiBridge: connessione a '%s'", ssid)
            self._wlan.connect(ssid, _CFG.get("PASSWORD", ""))
            for _ in range(50):   # max 10s
                if self._wlan.isconnected():
                    logger.info("WiFiBridge: IP=%s", self._wlan.ifconfig()[0])
                    return
                await uasyncio.sleep_ms(200)
            logger.warning("WiFiBridge: WiFi timeout connessione")
        except Exception as e:
            logger.warning("WiFiBridge: WiFi error: %s", e)

    async def _ping_rpi(self):
        """TCP connect rapido al RPi per testare raggiungibilità."""
        host, port = _rpi_host_port()
        try:
            r, w = await uasyncio.wait_for(
                uasyncio.open_connection(host, port),
                timeout=_CFG.get("PING_TIMEOUT_S", 2)
            )
            w.close()
            await w.wait_closed()
            return True
        except Exception:
            return False

    # ---------------------------------------------------------------
    # HTTP asincrono (raw socket, no urequests)
    # ---------------------------------------------------------------

    async def _send_direct(self, packet_str):
        try:
            expr, req_type, action = _parse_packet(packet_str)
        except Exception as e:
            return "error:BadPacket:" + str(e)[:20]

        host, port  = _rpi_host_port()
        token       = _CFG.get("API_TOKEN", "")
        timeout     = _CFG.get("TIMEOUT_S", 10)
        path        = _CFG.get("API_PATH", "/solve")

        body = ujson.dumps({
            "expression": expr,
            "type":       req_type,
            "action":     action,
        })

        headers  = "Content-Type: application/json\r\n"
        headers += "Content-Length: {}\r\n".format(len(body))
        if token:
            headers += "Authorization: Bearer {}\r\n".format(token)
        headers += "Connection: close\r\n"

        request = "POST {} HTTP/1.0\r\nHost: {}:{}\r\n{}\r\n{}".format(
            path, host, port, headers, body)

        try:
            r, w = await uasyncio.wait_for(
                uasyncio.open_connection(host, port),
                timeout=timeout
            )
            w.write(request.encode())
            await w.drain()

            raw = b""
            while True:
                try:
                    chunk = await uasyncio.wait_for(r.read(512), timeout=timeout)
                except uasyncio.TimeoutError:
                    break
                if not chunk:
                    break
                raw += chunk

            w.close()
            await w.wait_closed()
            return _parse_http(raw)

        except uasyncio.TimeoutError:
            if self._solve_mode == "auto":
                logger.warning("WiFiBridge: RPi timeout, switch a BLE")
                self._use_direct = False
                self._last_check = time.time()
            return "error:RPi timeout"
        except OSError as e:
            if self._solve_mode == "auto":
                self._use_direct = False
                self._last_check = time.time()
            return "error:OSError:" + str(e)[:25]
        except Exception as e:
            return "error:" + str(e)[:30]

    async def _send_phone(self, packet_str):
        try:
            expr, req_type, action = _parse_packet(packet_str)
        except Exception as e:
            return "error:BadPacket:" + str(e)[:20]

        phone_url = _CFG.get("PHONE_URL", "http://192.168.43.1:8765")
        token     = _CFG.get("PHONE_TOKEN", "")
        path      = _CFG.get("PHONE_PATH", "/solve")
        timeout   = _CFG.get("TIMEOUT_S", 10)

        # Estrai host:port
        url = phone_url
        for prefix in ("https://", "http://"):
            if url.startswith(prefix):
                url = url[len(prefix):]
        hostport = url.split("/")[0]
        host, port = (hostport.rsplit(":", 1) if ":" in hostport else (hostport, "80"))
        port = int(port)

        body = ujson.dumps({"expression": expr, "type": req_type, "action": action})
        headers  = "Content-Type: application/json\r\n"
        headers += "Content-Length: {}\r\n".format(len(body))
        if token:
            headers += "Authorization: Bearer {}\r\n".format(token)
        headers += "Connection: close\r\n"

        request = "POST {} HTTP/1.0\r\nHost: {}:{}\r\n{}\r\n{}".format(
            path, host, port, headers, body)

        try:
            r, w = await uasyncio.wait_for(
                uasyncio.open_connection(host, port), timeout=timeout)
            w.write(request.encode())
            await w.drain()
            raw = b""
            while True:
                try:
                    chunk = await uasyncio.wait_for(r.read(512), timeout=timeout)
                except uasyncio.TimeoutError:
                    break
                if not chunk:
                    break
                raw += chunk
            w.close()
            await w.wait_closed()
            return _parse_http(raw)
        except Exception as e:
            logger.warning("WiFiBridge: phone HTTP error: %s", e)
            return "error:Phone:" + str(e)[:25]


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _parse_http(raw):
    try:
        sep = raw.find(b"\r\n\r\n")
        if sep == -1:
            return "error:BadHTTP"
        status_line = raw[:raw.find(b"\r\n")].decode()
        status      = int(status_line.split(" ")[1])
        body        = raw[sep + 4:].decode()
        data        = ujson.loads(body)
        if status == 200:
            result = data.get("result", "")
            return "result:" + str(result) if result else "error:EmptyResult"
        detail = data.get("detail") or data.get("error") or "HTTP{}".format(status)
        return "error:" + str(detail)[:40]
    except Exception as e:
        return "error:ParseHTTP:" + str(e)[:20]


def _parse_packet(s):
    """'("expr", "type", "action", None)' → (expr, type, action|None)"""
    s = s.strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    tokens = _split_tl(s)
    if len(tokens) < 2:
        raise ValueError("need ≥2 fields")
    action = None
    if len(tokens) >= 3:
        raw = tokens[2].strip()
        if raw not in ("None", "none", ""):
            action = _unq(raw)
    return _unq(tokens[0]), _unq(tokens[1]), action


def _split_tl(s):
    tokens, cur, q = [], [], None
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch; cur.append(ch)
        elif ch == ",":
            tokens.append("".join(cur).strip()); cur = []
        else:
            cur.append(ch)
    if cur:
        tokens.append("".join(cur).strip())
    return tokens


def _unq(s):
    s = s.strip()
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        return s[1:-1]
    return s