"""IO module for data containers, adapters, and mappers.

This module provides:
- Containers: Data structures for documents and datasets
- Adapters: Convert external formats (CDA, CDS Hooks) to/from HealthChain
- Mappers: Transform clinical data between formats (FHIR to pandas, FHIR versions)
"""

from .containers import DataContainer, Document, Dataset, FeatureSchema
from .adapters.base import BaseAdapter
from .adapters.cdaadapter import CdaAdapter
from .adapters.cdsfhiradapter import CdsFhirAdapter
from .mappers import BaseMapper, FHIRFeatureMapper
from .types import TimeWindow, ValidationResult

__all__ = [
    # Containers
    "DataContainer",
    "Document",
    "Dataset",
    "FeatureSchema",
    # Adapters
    "BaseAdapter",
    "CdaAdapter",
    "CdsFhirAdapter",
    # Mappers
    "BaseMapper",
    "FHIRFeatureMapper",
    # Types
    "TimeWindow",
    "ValidationResult",
]
