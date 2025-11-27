import warnings

from .sandboxclient import SandboxClient
from .datasets import DatasetRegistry, DatasetLoader, list_available_datasets

# Import loaders to trigger auto-registration
from . import loaders  # noqa: F401

__all__ = [
    "SandboxClient",
    "DatasetRegistry",
    "DatasetLoader",
    "list_available_datasets",
]


def __getattr__(name):
    deprecated_names = [
        "sandbox",
        "api",
        "ehr",
        "ClinicalDecisionSupport",
        "ClinicalDocumentation",
    ]

    if name in deprecated_names:
        warnings.warn(
            f"{name} is deprecated and has been removed. "
            f"Use SandboxClient instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        raise AttributeError(f"{name} has been removed")
    raise AttributeError(f"module 'healthchain.sandbox' has no attribute '{name}'")
