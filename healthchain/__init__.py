import logging
from .utils.logger import ColorLogger


logging.setLoggerClass(ColorLogger)
logger = logging.getLogger(__name__)
