"""
Data models for Healthcare Data Format Converter.

Defines the request/response structures and enumerations for conversion operations.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConversionFormat(str, Enum):
    """Supported data formats for conversion."""

    FHIR = "fhir"
    CDA = "cda"
    HL7V2 = "hl7v2"


class DocumentType(str, Enum):
    """Supported CDA document types."""

    CCD = "ccd"  # Continuity of Care Document
    DISCHARGE_SUMMARY = "discharge_summary"
    PROGRESS_NOTE = "progress_note"
    CONSULTATION_NOTE = "consultation_note"
    HISTORY_AND_PHYSICAL = "history_and_physical"
    OPERATIVE_NOTE = "operative_note"
    PROCEDURE_NOTE = "procedure_note"
    REFERRAL_NOTE = "referral_note"


class ValidationLevel(str, Enum):
    """Validation strictness levels."""

    STRICT = "strict"  # Full validation, fails on errors
    WARN = "warn"      # Logs warnings but continues
    IGNORE = "ignore"  # No validation


class ConversionStatus(str, Enum):
    """Status of a conversion operation."""

    SUCCESS = "success"
    PARTIAL = "partial"  # Some resources converted with warnings
    FAILED = "failed"


class ResourceSummary(BaseModel):
    """Summary of a converted resource."""

    resource_type: str = Field(..., description="FHIR resource type")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    status: str = Field("converted", description="Conversion status")
    warnings: list[str] = Field(default_factory=list, description="Conversion warnings")


class ConversionMetadata(BaseModel):
    """Metadata about the conversion operation."""

    conversion_id: str = Field(..., description="Unique conversion identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_format: ConversionFormat
    target_format: ConversionFormat
    document_type: Optional[DocumentType] = None
    validation_level: ValidationLevel = ValidationLevel.WARN
    processing_time_ms: Optional[float] = None
    resource_count: int = 0
    warning_count: int = 0
    error_count: int = 0


class ConversionRequest(BaseModel):
    """Request payload for data conversion."""

    data: str | dict[str, Any] = Field(
        ...,
        description="Input data - XML string for CDA, JSON/dict for FHIR"
    )
    source_format: ConversionFormat = Field(
        ...,
        description="Source data format"
    )
    target_format: ConversionFormat = Field(
        ...,
        description="Target data format"
    )
    document_type: DocumentType = Field(
        default=DocumentType.CCD,
        description="Document type for CDA output"
    )
    validation_level: ValidationLevel = Field(
        default=ValidationLevel.WARN,
        description="Validation strictness level"
    )
    include_narrative: bool = Field(
        default=True,
        description="Include human-readable narrative in CDA"
    )
    preserve_ids: bool = Field(
        default=True,
        description="Preserve original resource IDs when possible"
    )
    custom_config: Optional[dict[str, Any]] = Field(
        default=None,
        description="Custom configuration overrides"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "data": "<ClinicalDocument>...</ClinicalDocument>",
                "source_format": "cda",
                "target_format": "fhir",
                "document_type": "ccd",
                "validation_level": "warn"
            }
        }


class ConversionResponse(BaseModel):
    """Response payload from data conversion."""

    status: ConversionStatus = Field(..., description="Conversion status")
    data: Optional[str | dict[str, Any] | list[dict[str, Any]]] = Field(
        None,
        description="Converted data - XML string for CDA, JSON for FHIR"
    )
    metadata: ConversionMetadata = Field(..., description="Conversion metadata")
    resources: list[ResourceSummary] = Field(
        default_factory=list,
        description="Summary of converted resources"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Conversion warnings"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Conversion errors (if status is failed)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {"resourceType": "Bundle", "entry": []},
                "metadata": {
                    "conversion_id": "conv-12345",
                    "source_format": "cda",
                    "target_format": "fhir",
                    "resource_count": 5
                },
                "resources": [
                    {"resource_type": "Condition", "resource_id": "cond-1"}
                ]
            }
        }


class BatchConversionRequest(BaseModel):
    """Request for batch conversion of multiple documents."""

    documents: list[ConversionRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of documents to convert"
    )
    parallel: bool = Field(
        default=True,
        description="Process documents in parallel"
    )
    stop_on_error: bool = Field(
        default=False,
        description="Stop processing if any document fails"
    )


class BatchConversionResponse(BaseModel):
    """Response from batch conversion."""

    total: int = Field(..., description="Total documents processed")
    successful: int = Field(..., description="Successfully converted documents")
    failed: int = Field(..., description="Failed conversions")
    results: list[ConversionResponse] = Field(
        ...,
        description="Individual conversion results"
    )
    processing_time_ms: float = Field(..., description="Total processing time")


class HealthCheckResponse(BaseModel):
    """API health check response."""

    status: str = Field(default="healthy")
    version: str
    supported_formats: list[str]
    supported_document_types: list[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversionCapabilities(BaseModel):
    """Describes the conversion capabilities of the service."""

    supported_conversions: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of supported source->target format pairs"
    )
    supported_document_types: list[str] = Field(
        default_factory=list,
        description="Supported CDA document types"
    )
    supported_fhir_resources: list[str] = Field(
        default_factory=list,
        description="FHIR resource types that can be converted"
    )
    max_batch_size: int = Field(default=100)
    validation_levels: list[str] = Field(
        default_factory=lambda: [v.value for v in ValidationLevel]
    )
