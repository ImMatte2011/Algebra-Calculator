try:
    from ubluetooth import BLE, UUID, FLAG_NOTIFY, FLAG_WRITE, FLAG_READ
except ImportError:
    BLE = None

from esp32.config import CONFIG
from esp32.utils.logger import logger


class BLEBridge:
    def __init__(self):
        self.ble = None
        self.expr_handle = None
        self.result_handle = None
        self._result = ""
        self._init_ble()

    def _init_ble(self):
        if BLE is None:
            logger.warning("ubluetooth not available, BLE bridge disabled")
            return

        self.ble = BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)

        expr_uuid = UUID(CONFIG["BLE_EXPR_CHAR_UUID"])
        result_uuid = UUID(CONFIG["BLE_RESULT_CHAR_UUID"])
        service_uuid = UUID(CONFIG["BLE_SERVICE_UUID"])

        expr_char = (expr_uuid, FLAG_WRITE | FLAG_READ)
        result_char = (result_uuid, FLAG_NOTIFY | FLAG_READ)
        service = (service_uuid, (expr_char, result_char))

        handles = self.ble.gatts_register_services((service,))
        self.expr_handle = handles[0][0]
        self.result_handle = handles[0][1]
        self.ble.gap_advertise(100_000, b"\x02\x01\x06" + bytes((len(CONFIG["BLE_NAME"]) + 1, 0x09)) + CONFIG["BLE_NAME"].encode())
        logger.info("BLE bridge initialized")

    def _irq(self, event, data):
        logger.debug(f"BLE IRQ event={event} data={data}")

    def send_expression(self, expr: str):
        if self.ble is None:
            logger.warning("BLE unavailable, cannot send expression")
            return
        logger.info(f"BLE sending expression: {expr}")
        self.ble.gatts_write(self.expr_handle, expr.encode())

    def read_result(self, timeout_ms: int = 5000) -> str:
        if self.ble is None:
            return "BLE unavailable"

        self._result = ""
        # Placeholder: read characteristic notification or local result store.
        return self._result
