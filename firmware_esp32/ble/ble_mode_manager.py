"""
ble_mode_manager.py — Gestione switch BLE central ↔ peripheral.

Importato SOLO da main.py quando CONFIG["KEYPAD_TYPE"] == "ble_hid".
Chi usa un keypad matriciale non carica mai questo modulo.

Flusso:
  FASE 1  ESP32 come CENTRAL → connesso al macropad BLE HID
          (KeypadBleHid usa questa istanza BLE come central)
  FASE 2  Utente preme ENTER → invio espressione
          switch_to_peripheral() → disconnette macropad, diventa server BLE
          Il telefono si connette, manda il risultato, si disconnette
  FASE 3  switch_to_central() → si riconnette al macropad

Latenza stimata per ogni switch: 1-3 secondi.
"""

import ubluetooth
import time
from utils import logger

class BleModeManager:

    MODE_CENTRAL    = "central"
    MODE_PERIPHERAL = "peripheral"
    MODE_SWITCHING  = "switching"
    MODE_IDLE       = "idle"

    def __init__(self, ble_bridge, keypad_ble):
        """
        Args:
            ble_bridge: istanza di BlePeripheral / BleServer (il server verso il telefono)
            keypad_ble: istanza di KeypadBleHid (il client verso il macropad)
        """
        self._bridge  = ble_bridge
        self._keypad  = keypad_ble
        self._mode    = self.MODE_CENTRAL
        self._pending_packet = None

        # Callback opzionale per aggiornare il display durante lo switch
        self.on_mode_change = None

    # -----------------------------------------------------------------------
    # API pubblica
    # -----------------------------------------------------------------------
    def current_mode(self):
        return self._mode

    def switch_to_peripheral(self, packet):
        """
        Chiamato quando l'utente ha premuto ENTER e c'è un pacchetto da inviare.
        Disconnette il macropad, passa in modalità peripheral e avvia advertising.

        Args:
            packet: tupla (expression, type, action, val) da inviare al telefono
        """
        if self._mode != self.MODE_CENTRAL:
            logger.warning("BleModeManager: switch_to_peripheral ignorato, modo=%s", self._mode)
            return

        self._pending_packet = packet
        self._mode = self.MODE_SWITCHING
        self._notify("switching_to_phone")
        logger.info("BleModeManager: switch → peripheral")

        # 1. Disconnetti il macropad (KeypadBleHid gestirà il reconnect dopo)
        #    L'istanza BLE è condivisa — fermiamo solo la parte central
        try:
            if self._keypad.is_connected():
                # gap_connect(None) non esiste in ubluetooth — la disconnessione
                # avviene implicitamente quando si avvia gap_advertise.
                # KeypadBleHid rileva _IRQ_PERIPHERAL_DISCONNECT e mette in coda
                # il reconnect con il suo timer.
                pass
        except Exception as e:
            logger.warning("BleModeManager: errore disconnect macropad: %s", e)

        # 2. Avvia il server BLE peripheral (advertising verso il telefono)
        try:
            self._bridge.start_advertising(force=True)
            self._mode = self.MODE_PERIPHERAL
            self._notify("peripheral_ready")
            logger.info("BleModeManager: advertising avviato, aspetto il telefono")
        except Exception as e:
            logger.warning("BleModeManager: errore avvio advertising: %s", e)
            self._mode = self.MODE_CENTRAL   # fallback

    def switch_to_central(self):
        """
        Chiamato dopo che il telefono si è disconnesso (risultato ricevuto o timeout).
        Ferma advertising e torna in modalità central (il macropad si riconnette da solo).
        """
        if self._mode == self.MODE_CENTRAL:
            return

        logger.info("BleModeManager: switch → central")
        self._mode = self.MODE_SWITCHING

        try:
            self._bridge.stop_advertising()
        except Exception as e:
            logger.warning("BleModeManager: errore stop advertising: %s", e)

        # KeypadBleHid si riconnette autonomamente grazie al suo timer
        # (RECONNECT_DELAY_MS) — non serve forzare nulla qui
        self._pending_packet = None
        self._mode = self.MODE_CENTRAL
        self._notify("central_ready")
        logger.info("BleModeManager: tornato in central, macropad si riconnette")

    def get_pending_packet(self):
        """Restituisce il pacchetto in attesa di invio (dopo switch_to_peripheral)."""
        return self._pending_packet

    def poll(self):
        """
        Chiamato ogni iterazione del loop principale in modalità peripheral.
        Controlla se il telefono si è connesso e ha ricevuto il pacchetto.
        """
        if self._mode != self.MODE_PERIPHERAL:
            return

        # Invia il pacchetto al telefono appena si connette
        if self._bridge.is_connected() and self._pending_packet is not None:
            packet_str = str(self._pending_packet)
            try:
                self._bridge.send_result(packet_str)
                logger.info("BleModeManager: pacchetto inviato al telefono")
                self._pending_packet = None
            except Exception as e:
                logger.warning("BleModeManager: errore invio pacchetto: %s", e)

    def _notify(self, state):
        if self.on_mode_change:
            try:
                self.on_mode_change(state)
            except Exception:
                pass