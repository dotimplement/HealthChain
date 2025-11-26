"""Clinical data mappers for transformations between formats.

Mappers handle transformations between different clinical data formats:
- FHIR to pandas (ML feature extraction)
- FHIR version migrations
- Clinical standard conversions (FHIR to OMOP)
"""

from .base import BaseMapper
from .fhirfeaturemapper import FHIRFeatureMapper

__all__ = ["BaseMapper", "FHIRFeatureMapper"]
