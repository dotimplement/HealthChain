# New simplified API
from .sandbox_client import SandboxClient
from .datasets import DatasetRegistry, DatasetLoader, list_available_datasets

# Import loaders to trigger auto-registration

# Legacy decorators and classes (deprecated)
from .decorator import sandbox, api, ehr
from .environment import SandboxEnvironment
from .use_cases import (
    ClinicalDecisionSupport,
    ClinicalDocumentation,
    CdsRequestConstructor,
    ClinDocRequestConstructor,
)
from .clients import EHRClient

__all__ = [
    # New API
    "SandboxClient",
    "DatasetRegistry",
    "DatasetLoader",
    "list_available_datasets",
    # Legacy API (deprecated)
    "sandbox",
    "api",
    "ehr",
    "SandboxEnvironment",
    "ClinicalDecisionSupport",
    "ClinicalDocumentation",
    "CdsRequestConstructor",
    "ClinDocRequestConstructor",
    "EHRClient",
]
