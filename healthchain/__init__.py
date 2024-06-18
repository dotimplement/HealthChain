import logging
from .utils.logger import add_handlers

from .decorators import api, sandbox
from .clients import ehr

logger = logging.getLogger(__name__)
add_handlers(logger)
logger.setLevel(logging.INFO)

# Export them at the top level
__all__ = ["ehr", "api", "sandbox"]
