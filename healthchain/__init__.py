import warnings

from .utils.logger import get_logger
from .config.base import ConfigManager, ValidationLevel


# Enable deprecation warnings
warnings.filterwarnings("always", category=DeprecationWarning, module="healthchain")

logger = get_logger(__name__)

# Export them at the top level
__all__ = ["ConfigManager", "ValidationLevel", "api", "ehr", "sandbox"]


# Legacy import with warning
def __getattr__(name):
    if name == "data_generators":
        warnings.warn(
            "Importing data_generators from healthchain is deprecated. "
            "Use 'from healthchain.sandbox import generators' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from healthchain.sandbox import generators

        return generators
    elif name == "use_cases":
        warnings.warn(
            "Importing use_cases from healthchain is deprecated. "
            "Use 'from healthchain.sandbox import use_cases' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from healthchain.sandbox import use_cases

        return use_cases
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
