"""
ble_mode_manager.py — Manages the BLE central ↔ peripheral switch.

Imported only by main.py when CONFIG["KEYPAD_TYPE"] == "ble_hid".
Users of a matrix keypad never load this module.

Flow:
  PHASE 1  ESP32 as CENTRAL → connected to the BLE HID macropad
          (KeypadBleHid uses this BLE instance as central)
  PHASE 2  User presses ENTER → send expression
          switch_to_peripheral() → disconnects the macropad, becomes a BLE server
          The phone connects, sends the result, and disconnects
  PHASE 3  switch_to_central() → reconnects to the macropad

Estimated latency per switch: 1-3 seconds.
"""

import ubluetooth
import time
from utils import logger
from config import CONFIG

class BleModeManager:

    MODE_CENTRAL    = "central"
    MODE_PERIPHERAL = "peripheral"
    MODE_SWITCHING  = "switching"
    MODE_IDLE       = "idle"

    def __init__(self, ble_bridge, keypad_ble):
        """
        Args:
            ble_bridge: instance of BlePeripheral / BleServer (the server toward the phone)
            keypad_ble: instance of KeypadBleHid (the client toward the macropad)
        """
        self._bridge  = ble_bridge
        self._keypad  = keypad_ble
        self._mode    = self.MODE_CENTRAL
        self._pending_packet = None

        # Optional callback to update the display during the switch
        self.on_mode_change = None

        self._peripheral_start = 0
        self._mac_checked      = False

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    def current_mode(self):
        return self._mode

    def switch_to_peripheral(self, packet):
        """
        Called when the user has pressed ENTER and there is a packet to send.
        Disconnects the macropad, switches to peripheral mode, and starts advertising.

        Args:
            packet: tuple (expression, type, action, val) to send to the phone
        """
        if self._mode != self.MODE_CENTRAL:
            logger.warning("BleModeManager: switch_to_peripheral ignored, mode=%s", self._mode)
            return

        self._pending_packet = packet
        self._mode = self.MODE_SWITCHING
        self._notify("switching_to_phone")
        logger.info("BleModeManager: switch → peripheral")

        # 1. Disconnect the macropad (KeypadBleHid will handle the reconnect afterward)
        #    The BLE instance is shared — stop only the central side
        try:
            if self._keypad.is_connected():
                # gap_connect(None) does not exist in ubluetooth — the disconnect
                # happens implicitly when gap_advertise is started.
                # KeypadBleHid detects _IRQ_PERIPHERAL_DISCONNECT and queues
                # the reconnect with its timer.
                pass
        except Exception as e:
            logger.warning("BleModeManager: macropad disconnect error: %s", e)

        self._peripheral_start = time.time()
        self._mac_checked      = False

        # 2. Start the BLE peripheral server (advertising toward the phone)
        try:
            self._bridge.start_advertising(force=True)
            self._mode = self.MODE_PERIPHERAL
            self._notify("peripheral_ready")
            logger.info("BleModeManager: advertising started, waiting for the phone")
        except Exception as e:
            logger.warning("BleModeManager: advertising start error: %s", e)
            self._mode = self.MODE_CENTRAL   # fallback

    def switch_to_central(self):
        """
        Called after the phone disconnects (result received or timeout).
        Stops advertising and returns to central mode (the macropad reconnects by itself).
        """
        if self._mode == self.MODE_CENTRAL:
            return

        logger.info("BleModeManager: switch → central")
        self._mode = self.MODE_SWITCHING

        try:
            self._bridge.stop_advertising()
        except Exception as e:
            logger.warning("BleModeManager: advertising stop error: %s", e)

        # KeypadBleHid reconnects automatically via its timer
        # (RECONNECT_DELAY_MS) — no need to force anything here
        self._pending_packet = None
        self._mode = self.MODE_CENTRAL
        self._notify("central_ready")
        logger.info("BleModeManager: returned to central, macropad reconnects")

    def get_pending_packet(self):
        """Returns the packet waiting to be sent (after switch_to_peripheral)."""
        return self._pending_packet

    def poll(self):
        """
        Chiamato a ogni ciclo del main loop in modalità peripheral.

        Ritorni possibili:
        None                      → non siamo in modalità peripheral
        {"countdown": N}          → in attesa del telefono, N secondi al timeout
        {"timeout": True}         → timeout scaduto, siamo tornati a central
        """
        if self._mode != self.MODE_PERIPHERAL:
            return None

        timeout_s = CONFIG.get("BLE_PHONE_TIMEOUT_S", 30)
        elapsed   = int(time.time() - self._peripheral_start)
        remaining = max(0, timeout_s - elapsed)

        # --- Timeout: telefono non connesso entro il limite (Punto 3) ---
        if elapsed >= timeout_s and not self._bridge.is_connected():
            logger.info("BleModeManager: timeout telefono, ritorno a centrale")
            self.switch_to_central()
            return {"timeout": True}

        # --- MAC Whitelist: controlla alla prima connessione (Punto 1) ---
        if self._bridge.is_connected() and not self._mac_checked:
            self._mac_checked = True
            allowed = CONFIG.get("PHONE_MAC", "").upper().strip()
            peer    = self._bridge.get_peer_addr_str()
            if allowed and allowed != "XX:XX:XX:XX:XX:XX" and peer != allowed:
                logger.warning("BleModeManager: MAC %s non in whitelist, disconnessione", peer)
                self._bridge.disconnect()
                self._mac_checked = False   # reset per il prossimo tentativo
                return {"countdown": remaining}

        # --- Invia pacchetto appena il telefono si connette ---
        if self._bridge.is_connected() and self._pending_packet is not None:
            packet_str = str(self._pending_packet)
            try:
                self._bridge.send_result(packet_str)
                logger.info("BleModeManager: pacchetto inviato al telefono")
                self._pending_packet = None
            except Exception as e:
                logger.warning("BleModeManager: errore invio pacchetto: %s", e)

        return {"countdown": remaining}

    def _notify(self, state):
        if self.on_mode_change:
            try:
                self.on_mode_change(state)
            except Exception:
                pass