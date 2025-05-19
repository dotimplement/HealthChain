import warnings

# Issue deprecation warning
warnings.warn(
    "The 'healthchain.use_cases' module is deprecated. Please use 'healthchain.sandbox.use_cases' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import everything from the new location
from healthchain.sandbox.use_cases import *  # noqa: E402 F403
