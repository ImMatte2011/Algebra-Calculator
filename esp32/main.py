from esp32.config import CONFIG
from esp32.core.input_manager import InputManager
from esp32.core.ui_manager import UIManager
from esp32.network.ble_bridge import BLEBridge
from esp32.utils.logger import logger


def main():
    logger.info("Starting ESP32 calculator application")

    input_manager = InputManager()
    ui_manager = UIManager()
    ble_bridge = BLEBridge()

    ui_manager.show_message("Calc ready")

    while True:
        key = input_manager.read_key()
        if key is None:
            continue

        ui_manager.update_expression(input_manager.expression)

        if input_manager.is_submit():
            expression = input_manager.expression
            logger.info(f"Submitting expression: {expression}")
            ble_bridge.send_expression(expression)
            result = ble_bridge.read_result()
            ui_manager.show_result(result)
            input_manager.reset()


if __name__ == "__main__":
    main()
