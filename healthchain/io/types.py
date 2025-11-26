"""Type definitions for IO operations.

This module provides common types used across IO operations, particularly
for FHIR to Dataset data conversion.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from pydantic import BaseModel, Field, field_validator


class TimeWindow(BaseModel):
    """Defines a time window for filtering temporal data.

    Used to extract data from a specific time period relative to a reference point,
    such as the first 24 hours after ICU admission.

    Attributes:
        reference_field: Field name in the FHIR resource marking the reference time
            (e.g., "intime" for ICU admission, "admittime" for hospital admission)
        hours: Duration of the time window in hours from the reference point
        offset_hours: Number of hours to offset from the reference point (default: 0)
            For example, offset_hours=6 and hours=24 would capture hours 6-30

    Example:
        >>> # Capture first 24 hours after ICU admission
        >>> window = TimeWindow(reference_field="intime", hours=24)
        >>>
        >>> # Capture hours 6-30 after admission
        >>> window = TimeWindow(reference_field="admittime", hours=24, offset_hours=6)
    """

    reference_field: str
    hours: int
    offset_hours: int = Field(default=0)

    @field_validator("hours")
    @classmethod
    def hours_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("hours must be positive")
        return v

    @field_validator("offset_hours")
    @classmethod
    def offset_hours_non_negative(cls, v):
        if v < 0:
            raise ValueError("offset_hours must be non-negative")
        return v


@dataclass
class ValidationResult:
    """Result of data validation operations.

    Attributes:
        valid: Overall validation status
        missing_features: List of required features that are missing
        type_mismatches: Dictionary mapping feature names to (expected, actual) type tuples
        warnings: List of non-critical validation warnings
        errors: List of validation errors

    Example:
        >>> result = ValidationResult(
        ...     valid=False,
        ...     missing_features=["heart_rate"],
        ...     type_mismatches={"age": ("int64", "object")},
        ...     warnings=["Optional feature 'temperature' is missing"],
        ...     errors=["Required feature 'heart_rate' is missing"]
        ... )
    """

    valid: bool
    missing_features: List[str] = None
    type_mismatches: Dict[str, Tuple[str, str]] = None
    warnings: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        """Initialize empty lists and dicts for None values."""
        if self.missing_features is None:
            self.missing_features = []
        if self.type_mismatches is None:
            self.type_mismatches = {}
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []

    def __str__(self) -> str:
        """Human-readable validation result."""
        if self.valid:
            return "Validation passed"

        lines = ["Validation failed:"]

        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  - {error}")

        if self.missing_features:
            lines.append("\nMissing features:")
            for feature in self.missing_features:
                lines.append(f"  - {feature}")

        if self.type_mismatches:
            lines.append("\nType mismatches:")
            for feature, (expected, actual) in self.type_mismatches.items():
                lines.append(f"  - {feature}: expected {expected}, got {actual}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)

    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)

    def add_missing_feature(self, feature: str) -> None:
        """Add a missing feature."""
        self.missing_features.append(feature)
        self.errors.append(f"Required feature '{feature}' is missing")
        self.valid = False

    def add_type_mismatch(self, feature: str, expected: str, actual: str) -> None:
        """Add a type mismatch."""
        self.type_mismatches[feature] = (expected, actual)
        self.errors.append(
            f"Type mismatch for '{feature}': expected {expected}, got {actual}"
        )
