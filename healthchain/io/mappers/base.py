"""Base mapper for clinical data transformations.

Mappers handle transformations between different clinical data formats and
representations, including:
- Clinical standard conversions (FHIR versions, FHIR to OMOP)
- Feature extraction for ML (FHIR to pandas)
- Data model transformations
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

SourceType = TypeVar("SourceType")
TargetType = TypeVar("TargetType")


class BaseMapper(Generic[SourceType, TargetType], ABC):
    """
    Abstract base class for clinical data mappers.

    Mappers transform clinical data between different formats and representations,
    distinct from Adapters which handle external message format conversion.

    Use mappers for:
    - FHIR to pandas feature extraction (ML workflows)
    - FHIR version migrations (R4 to R5)
    - Clinical standard conversions (FHIR to OMOP)
    - Semantic and structural data transformations

    Example:
        >>> class FHIRFeatureMapper(BaseMapper[Bundle, pd.DataFrame]):
        ...     def map(self, source: Bundle) -> pd.DataFrame:
        ...         # Extract features from FHIR Bundle
        ...         return dataframe
    """

    @abstractmethod
    def map(self, source: SourceType) -> TargetType:
        """
        Transform source data to target format.

        Args:
            source: Source data in input format

        Returns:
            Transformed data in target format
        """
        pass
