"""
Shared types and enums for the interoperability engine.
"""

from enum import Enum


class FormatType(Enum):
    """Enum for supported healthcare data formats."""

    HL7V2 = "hl7v2"
    CDA = "cda"
    FHIR = "fhir"


def validate_format(format_type):
    """Validate and convert format type to enum"""
    if isinstance(format_type, str):
        try:
            return FormatType[format_type.upper()]
        except KeyError:
            raise ValueError(f"Unsupported format: {format_type}")
    else:
        return format_type
