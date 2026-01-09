"""
Healthcare Data Converter - Core conversion engine.

Provides bidirectional conversion between FHIR and CDA formats using
HealthChain's interop engine with configuration-driven templates.
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from fhir.resources.bundle import Bundle
from fhir.resources.resource import Resource

from healthchain.interop import InteropEngine, create_interop
from healthchain.interop.config_manager import InteropConfigManager, ValidationLevel as HCValidationLevel
from healthchain.interop.template_registry import TemplateRegistry

from healthcare_data_converter.models import (
    ConversionFormat,
    ConversionMetadata,
    ConversionRequest,
    ConversionResponse,
    ConversionStatus,
    DocumentType,
    ResourceSummary,
    ValidationLevel,
    ConversionCapabilities,
)

logger = logging.getLogger(__name__)


class HealthcareDataConverter:
    """
    Core healthcare data format converter.

    Provides bidirectional conversion between FHIR and CDA formats using
    configuration-driven Liquid templates. Built on HealthChain's InteropEngine.

    Examples:
        Basic usage:
        ```python
        converter = HealthcareDataConverter()

        # CDA to FHIR
        fhir_bundle = converter.cda_to_fhir(cda_xml)

        # FHIR to CDA
        cda_xml = converter.fhir_to_cda(fhir_resources, document_type="ccd")
        ```

        Using custom configuration:
        ```python
        converter = HealthcareDataConverter(
            config_dir="./custom_configs",
            template_dir="./custom_templates"
        )
        ```
    """

    # Mapping of our ValidationLevel to HealthChain's
    VALIDATION_MAP = {
        ValidationLevel.STRICT: HCValidationLevel.STRICT,
        ValidationLevel.WARN: HCValidationLevel.WARN,
        ValidationLevel.IGNORE: HCValidationLevel.IGNORE,
    }

    # Supported FHIR resources for conversion
    SUPPORTED_FHIR_RESOURCES = [
        "Condition",
        "MedicationStatement",
        "MedicationRequest",
        "AllergyIntolerance",
        "Observation",
        "Procedure",
        "Immunization",
        "DiagnosticReport",
        "DocumentReference",
        "Encounter",
        "Patient",
    ]

    def __init__(
        self,
        config_dir: Optional[str | Path] = None,
        template_dir: Optional[str | Path] = None,
        validation_level: ValidationLevel = ValidationLevel.WARN,
        default_document_type: DocumentType = DocumentType.CCD,
    ):
        """
        Initialize the healthcare data converter.

        Args:
            config_dir: Path to configuration directory (uses HealthChain defaults if None)
            template_dir: Path to template directory (uses HealthChain defaults if None)
            validation_level: Default validation strictness level
            default_document_type: Default CDA document type for FHIR->CDA conversion
        """
        self.config_dir = Path(config_dir) if config_dir else None
        self.template_dir = Path(template_dir) if template_dir else None
        self.validation_level = validation_level
        self.default_document_type = default_document_type

        # Initialize the underlying HealthChain engine
        self._engine = self._create_engine()

        logger.info(
            f"HealthcareDataConverter initialized with validation_level={validation_level.value}"
        )

    def _create_engine(self) -> InteropEngine:
        """Create and configure the InteropEngine instance."""
        # Convert ValidationLevel enum to string value
        validation_level_str = self.validation_level.value  # e.g., "strict", "warn", "ignore"

        # Use create_interop helper which handles None config_dir automatically
        if self.config_dir:
            return create_interop(
                config_dir=self.config_dir,
                validation_level=validation_level_str,
                environment="development"
            )
        else:
            # Use bundled configs (create_interop will auto-discover)
            return create_interop(
                config_dir=None,
                validation_level=validation_level_str,
                environment="development"
            )

    def convert(self, request: ConversionRequest) -> ConversionResponse:
        """
        Convert data between formats based on the request.

        Args:
            request: Conversion request with source data and format specifications

        Returns:
            ConversionResponse with converted data and metadata
        """
        start_time = time.perf_counter()
        conversion_id = f"conv-{uuid.uuid4().hex[:12]}"
        warnings: list[str] = []
        errors: list[str] = []
        resources: list[ResourceSummary] = []
        converted_data = None
        status = ConversionStatus.SUCCESS

        try:
            # Route to appropriate conversion method
            if request.source_format == ConversionFormat.CDA:
                if request.target_format == ConversionFormat.FHIR:
                    converted_data, resources = self._convert_cda_to_fhir(
                        request.data, warnings
                    )
                else:
                    errors.append(
                        f"Unsupported conversion: {request.source_format} -> {request.target_format}"
                    )
                    status = ConversionStatus.FAILED

            elif request.source_format == ConversionFormat.FHIR:
                if request.target_format == ConversionFormat.CDA:
                    converted_data = self._convert_fhir_to_cda(
                        request.data,
                        request.document_type,
                        request.include_narrative,
                        warnings,
                    )
                    resources = self._extract_resource_summaries(request.data)
                else:
                    errors.append(
                        f"Unsupported conversion: {request.source_format} -> {request.target_format}"
                    )
                    status = ConversionStatus.FAILED

            elif request.source_format == ConversionFormat.HL7V2:
                if request.target_format == ConversionFormat.FHIR:
                    converted_data, resources = self._convert_hl7v2_to_fhir(
                        request.data, warnings
                    )
                else:
                    errors.append(
                        f"Unsupported conversion: {request.source_format} -> {request.target_format}"
                    )
                    status = ConversionStatus.FAILED

            else:
                errors.append(f"Unsupported source format: {request.source_format}")
                status = ConversionStatus.FAILED

            # Determine final status
            if status != ConversionStatus.FAILED:
                if warnings:
                    status = ConversionStatus.PARTIAL
                else:
                    status = ConversionStatus.SUCCESS

        except Exception as e:
            logger.exception(f"Conversion failed: {e}")
            errors.append(str(e))
            status = ConversionStatus.FAILED

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        metadata = ConversionMetadata(
            conversion_id=conversion_id,
            source_format=request.source_format,
            target_format=request.target_format,
            document_type=request.document_type if request.target_format == ConversionFormat.CDA else None,
            validation_level=request.validation_level,
            processing_time_ms=round(elapsed_ms, 2),
            resource_count=len(resources),
            warning_count=len(warnings),
            error_count=len(errors),
        )

        return ConversionResponse(
            status=status,
            data=converted_data,
            metadata=metadata,
            resources=resources,
            warnings=warnings,
            errors=errors,
        )

    def cda_to_fhir(
        self,
        cda_xml: str,
        validation_level: Optional[ValidationLevel] = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """
        Convert CDA XML to FHIR resources.

        Args:
            cda_xml: CDA XML document string
            validation_level: Override default validation level

        Returns:
            Tuple of (list of FHIR resources as dicts, list of warnings)
        """
        warnings: list[str] = []
        resources, _ = self._convert_cda_to_fhir(cda_xml, warnings)
        return resources, warnings

    def fhir_to_cda(
        self,
        fhir_data: str | dict | list | Bundle,
        document_type: Optional[DocumentType] = None,
        include_narrative: bool = True,
        validation_level: Optional[ValidationLevel] = None,
    ) -> tuple[str, list[str]]:
        """
        Convert FHIR resources to CDA XML.

        Args:
            fhir_data: FHIR resources (Bundle, list of resources, or JSON string)
            document_type: CDA document type (defaults to CCD)
            include_narrative: Include human-readable narrative sections
            validation_level: Override default validation level

        Returns:
            Tuple of (CDA XML string, list of warnings)
        """
        warnings: list[str] = []
        doc_type = document_type or self.default_document_type
        cda_xml = self._convert_fhir_to_cda(fhir_data, doc_type, include_narrative, warnings)
        return cda_xml, warnings

    def _convert_cda_to_fhir(
        self, cda_xml: str | dict, warnings: list[str]
    ) -> tuple[list[dict[str, Any]], list[ResourceSummary]]:
        """Internal CDA to FHIR conversion."""
        try:
            # Use HealthChain's interop engine
            fhir_resources = self._engine.to_fhir(cda_xml, src_format="cda")

            # Convert to list of dicts
            result = []
            summaries = []

            for resource in fhir_resources:
                if isinstance(resource, Resource):
                    resource_dict = json.loads(resource.model_dump_json())
                elif isinstance(resource, dict):
                    resource_dict = resource
                else:
                    warnings.append(f"Unexpected resource type: {type(resource)}")
                    continue

                result.append(resource_dict)
                summaries.append(
                    ResourceSummary(
                        resource_type=resource_dict.get("resourceType", "Unknown"),
                        resource_id=resource_dict.get("id"),
                        status="converted",
                    )
                )

            return result, summaries

        except Exception as e:
            logger.error(f"CDA to FHIR conversion error: {e}")
            raise

    def _convert_fhir_to_cda(
        self,
        fhir_data: str | dict | list | Bundle,
        document_type: DocumentType,
        include_narrative: bool,
        warnings: list[str],
    ) -> str:
        """Internal FHIR to CDA conversion."""
        try:
            # Normalize input to list of resources
            resources = self._normalize_fhir_input(fhir_data)

            # Use HealthChain's interop engine
            cda_xml = self._engine.from_fhir(
                resources,
                dest_format="cda",
                document_type=document_type.value,
                validate=self.validation_level != ValidationLevel.IGNORE,
            )

            return cda_xml

        except Exception as e:
            logger.error(f"FHIR to CDA conversion error: {e}")
            raise

    def _convert_hl7v2_to_fhir(
        self, hl7v2_message: str, warnings: list[str]
    ) -> tuple[list[dict[str, Any]], list[ResourceSummary]]:
        """Internal HL7v2 to FHIR conversion."""
        try:
            fhir_resources = self._engine.to_fhir(hl7v2_message, src_format="hl7v2")

            result = []
            summaries = []

            for resource in fhir_resources:
                if isinstance(resource, Resource):
                    resource_dict = json.loads(resource.model_dump_json())
                elif isinstance(resource, dict):
                    resource_dict = resource
                else:
                    warnings.append(f"Unexpected resource type: {type(resource)}")
                    continue

                result.append(resource_dict)
                summaries.append(
                    ResourceSummary(
                        resource_type=resource_dict.get("resourceType", "Unknown"),
                        resource_id=resource_dict.get("id"),
                        status="converted",
                    )
                )

            return result, summaries

        except Exception as e:
            logger.error(f"HL7v2 to FHIR conversion error: {e}")
            raise

    def _normalize_fhir_input(
        self, fhir_data: str | dict | list | Bundle
    ) -> list[Resource]:
        """Normalize various FHIR input formats to a list of resources."""
        if isinstance(fhir_data, str):
            fhir_data = json.loads(fhir_data)

        if isinstance(fhir_data, Bundle):
            return [entry.resource for entry in (fhir_data.entry or []) if entry.resource]

        if isinstance(fhir_data, dict):
            if fhir_data.get("resourceType") == "Bundle":
                bundle = Bundle.model_validate(fhir_data)
                return [entry.resource for entry in (bundle.entry or []) if entry.resource]
            else:
                # Single resource
                return [fhir_data]

        if isinstance(fhir_data, list):
            return fhir_data

        raise ValueError(f"Unsupported FHIR data type: {type(fhir_data)}")

    def _extract_resource_summaries(
        self, fhir_data: str | dict | list | Bundle
    ) -> list[ResourceSummary]:
        """Extract resource summaries from FHIR input."""
        resources = self._normalize_fhir_input(fhir_data)
        summaries = []

        for resource in resources:
            if isinstance(resource, Resource):
                summaries.append(
                    ResourceSummary(
                        resource_type=resource.resource_type,
                        resource_id=getattr(resource, "id", None),
                        status="converted",
                    )
                )
            elif isinstance(resource, dict):
                summaries.append(
                    ResourceSummary(
                        resource_type=resource.get("resourceType", "Unknown"),
                        resource_id=resource.get("id"),
                        status="converted",
                    )
                )

        return summaries

    def get_capabilities(self) -> ConversionCapabilities:
        """Get the conversion capabilities of this instance."""
        return ConversionCapabilities(
            supported_conversions=[
                {"source": "cda", "target": "fhir"},
                {"source": "fhir", "target": "cda"},
                {"source": "hl7v2", "target": "fhir"},
            ],
            supported_document_types=[dt.value for dt in DocumentType],
            supported_fhir_resources=self.SUPPORTED_FHIR_RESOURCES,
            max_batch_size=100,
            validation_levels=[vl.value for vl in ValidationLevel],
        )

    def validate_cda(self, cda_xml: str) -> tuple[bool, list[str]]:
        """
        Validate a CDA document.

        Args:
            cda_xml: CDA XML document string

        Returns:
            Tuple of (is_valid, list of validation messages)
        """
        from healthchain.interop.models.cda import ClinicalDocument
        import xmltodict

        messages = []
        try:
            doc_dict = xmltodict.parse(cda_xml)
            ClinicalDocument.model_validate(doc_dict.get("ClinicalDocument", {}))
            return True, []
        except Exception as e:
            messages.append(str(e))
            return False, messages

    def validate_fhir(self, fhir_data: str | dict | list) -> tuple[bool, list[str]]:
        """
        Validate FHIR resources.

        Args:
            fhir_data: FHIR resources (Bundle, list, or JSON string)

        Returns:
            Tuple of (is_valid, list of validation messages)
        """
        messages = []
        try:
            resources = self._normalize_fhir_input(fhir_data)
            for resource in resources:
                if isinstance(resource, dict):
                    resource_type = resource.get("resourceType")
                    if resource_type:
                        # Dynamic import based on resource type
                        from healthchain.fhir.helpers import create_resource_from_dict
                        create_resource_from_dict(resource_type, resource)
            return True, []
        except Exception as e:
            messages.append(str(e))
            return False, messages
