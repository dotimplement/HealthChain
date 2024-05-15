import logging
from .utils.logger import add_handlers


logger = logging.getLogger(__name__)
add_handlers(logger)
logger.setLevel(logging.INFO)
