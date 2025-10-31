"""
Dataset loaders package.

Auto-registers all available dataset loaders on import.
"""

from healthchain.sandbox.datasets import DatasetRegistry
from healthchain.sandbox.loaders.mimic import MimicOnFHIRLoader
from healthchain.sandbox.loaders.synthea import SyntheaFHIRPatientLoader

# Register loaders
DatasetRegistry.register(MimicOnFHIRLoader())
DatasetRegistry.register(SyntheaFHIRPatientLoader())

__all__ = ["MimicOnFHIRLoader", "SyntheaFHIRPatientLoader"]
