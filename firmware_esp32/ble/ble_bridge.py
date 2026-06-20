import ubluetooth
import time
from config import CONFIG
from utils import logger

class BLEBridge:
    _IRQ_CENTRAL_CONNECT = 1
    _IRQ_CENTRAL_DISCONNECT = 2
    _IRQ_GATTS_WRITE = 3

    def __init__(self, callback_on_receive=None, advertise_interval=5, inactivity_timeout=10):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)

        self.callback = callback_on_receive
        self.conn_handle = None
        self.last_activity = time.time()
        self.last_advertise = 0
        self.advertising = False
        self.advertise_interval = advertise_interval
        self.inactivity_timeout = inactivity_timeout
        self.rx_queue = []
        self.needs_advertise = True

        service_uuid = ubluetooth.UUID(CONFIG["BLE_SERVICE_UUID"])
        expr_uuid = ubluetooth.UUID(CONFIG["BLE_EXPR_CHAR_UUID"])
        result_uuid = ubluetooth.UUID(CONFIG["BLE_RESULT_CHAR_UUID"])

        expr_char = (expr_uuid, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_WRITE_NO_RESPONSE)
        result_char = (result_uuid, ubluetooth.FLAG_NOTIFY | ubluetooth.FLAG_READ)
        service = (service_uuid, (expr_char, result_char))

        ((self.expr_handle, self.result_handle),) = self.ble.gatts_register_services((service,))
        logger.info("BLE Bridge inizializzato")

    def _advertise(self):
        name = CONFIG["BLE_NAME"]
        payload = b'\x02\x01\x06' + bytes([len(name) + 1]) + b'\x09' + name.encode()
        self.ble.gap_advertise(100, payload)
        self.advertising = True
        self.last_advertise = time.time()
        self.needs_advertise = False
        logger.info("BLE advertising started")

    def start_advertising(self, force=False):
        if self.conn_handle is not None:
            return

        now = time.time()
        if not force and self.advertising and now - self.last_advertise < self.advertise_interval:
            return

        try:
            self._advertise()
        except Exception as e:
            logger.warning("BLE advertising error: %s", e)

    def stop_advertising(self):
        if not self.advertising:
            return

        try:
            self.ble.gap_advertise(None)
        except Exception as e:
            logger.warning("BLE stop advertising error: %s", e)
        finally:
            self.advertising = False

    def _clear_connection_state(self, reason=None):
        if self.conn_handle is None:
            return

        self.conn_handle = None
        self.advertising = False
        self.needs_advertise = True
        self.last_activity = time.time()

        if reason:
            logger.info(reason)

    def _irq(self, event, data):
        if event == self._IRQ_CENTRAL_CONNECT:
            self.conn_handle, _, _ = data
            self.last_activity = time.time()
            self.advertising = False
            self.needs_advertise = False
            logger.info("BLE connected")

        elif event == self._IRQ_CENTRAL_DISCONNECT:
            self._clear_connection_state("BLE disconnected")

        elif event == self._IRQ_GATTS_WRITE:
            self.last_activity = time.time()
            conn_handle, value_handle = data
            if value_handle == self.expr_handle:
                try:
                    payload = self.ble.gatts_read(self.expr_handle)
                    if payload:
                        self.rx_queue.append(payload)
                except Exception as e:
                    logger.warning("BLE read error in IRQ: %s", e)

    def check_connection(self):
        return self.is_connected()

    def _check_inactivity(self):
        if self.conn_handle is None:
            return

        if time.time() - self.last_activity > self.inactivity_timeout:
            self._clear_connection_state("BLE inactivity timeout: internal disconnect")

    def poll(self):
        self._check_inactivity()
        while self.rx_queue:
            payload = self.rx_queue.pop(0)
            try:
                message = payload.decode("utf-8")
                if self.callback:
                    self.callback(message)
            except Exception as e:
                logger.warning("BLE payload decode error: %s", e)

    def is_connected(self):
        self._check_inactivity()
        return self.conn_handle is not None

    def send_result(self, result_str):
        if self.conn_handle is not None:
            try:
                data = result_str.encode('utf-8')
                self.ble.gatts_write(self.result_handle, data)
                self.ble.gatts_notify(self.conn_handle, self.result_handle, data)
                self.last_activity = time.time()
                logger.info(f"Notifica inviata: {result_str}")
            except Exception as e:
                print("Errore invio BLE:", e)
        else:
            print("BLE non connesso, salto invio")