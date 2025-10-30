"""
Dataset loaders package.

Auto-registers all available dataset loaders on import.
"""

from healthchain.sandbox.datasets import DatasetRegistry
from healthchain.sandbox.loaders.mimic import MimicOnFHIRLoader

# Register loaders
DatasetRegistry.register(MimicOnFHIRLoader())
# DatasetRegistry.register(SyntheaLoader())  # if implemented

__all__ = ["MimicOnFHIRLoader"]
