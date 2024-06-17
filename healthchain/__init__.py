import logging
from .utils.logger import add_handlers
from healthchain.decorators import ehr, api, sandbox
from healthchain.data_generator.data_generator import CdsDataGenerator
from healthchain.models.requests.cdsrequest import CDSRequest

logger = logging.getLogger(__name__)
add_handlers(logger)
logger.setLevel(logging.INFO)

# Export them at the top level
__all__ = ["ehr", "api", "sandbox", "CdsDataGenerator", "CDSRequest"]
