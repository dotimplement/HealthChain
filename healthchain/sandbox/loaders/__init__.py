"""
Dataset loaders for SandboxClient.

This module provides loaders for various test datasets:
- MIMIC-on-FHIR: Real clinical data from MIMIC-IV
- Synthea: Synthetic patient data
"""

from healthchain.sandbox.loaders.mimic import MimicOnFHIRLoader
from healthchain.sandbox.loaders.synthea import SyntheaLoader

__all__ = [
    "MimicOnFHIRLoader",
    "SyntheaLoader",
]

# Auto-register loaders on import
from healthchain.sandbox.datasets import DatasetRegistry

DatasetRegistry.register(MimicOnFHIRLoader())
DatasetRegistry.register(SyntheaLoader())
