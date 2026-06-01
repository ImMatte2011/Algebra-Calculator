import logging
from rpi4.config import CONFIG


_LOG_LEVEL = CONFIG.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s",
)
logger = logging.getLogger("calc_algebraica")


def info(message: str):
    logger.info(message)


def error(message: str):
    logger.error(message)


def debug(message: str):
    logger.debug(message)
