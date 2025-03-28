import logging

from functools import cached_property
from enum import Enum
from typing import Dict, List, Union, Optional, Callable
from pathlib import Path

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle

from healthchain.config.base import ValidationLevel
from healthchain.interop.config_manager import InteropConfigManager

from healthchain.interop.parsers.cda import CDAParser
from healthchain.interop.parsers.hl7v2 import HL7v2Parser
from healthchain.interop.template_registry import TemplateRegistry
from healthchain.interop.generators.cda import CDAGenerator
from healthchain.interop.generators.fhir import FHIRGenerator
from healthchain.interop.generators.hl7v2 import HL7v2Generator
from healthchain.interop.filters import (
    format_date,
    map_system,
    map_status,
    clean_empty,
    format_timestamp,
    generate_id,
    to_json,
    extract_effective_period,
    extract_effective_timing,
    extract_clinical_status,
    extract_reactions,
    map_severity,
)
from healthchain.interop.utils import normalize_resource_list

log = logging.getLogger(__name__)


class FormatType(Enum):
    HL7V2 = "hl7v2"
    CDA = "cda"
    FHIR = "fhir"


def validate_format(format_type: Union[str, FormatType]) -> FormatType:
    if isinstance(format_type, str):
        try:
            return FormatType[format_type.upper()]
        except KeyError:
            raise ValueError(f"Unsupported format: {format_type}")
    else:
        return format_type


class InteropEngine:
    """Generic interoperability engine for converting between healthcare formats

    The InteropEngine provides capabilities for converting between different
    healthcare data format standards, such as HL7 FHIR, CDA, and HL7v2.

    Configuration is handled through the `config` property, which provides
    direct access to the underlying ConfigManager instance. This allows
    for setting validation levels, changing environments, and accessing
    configuration values.

    Example:
        engine = InteropEngine()
        # Access config directly:
        engine.config.set_environment("production")
        engine.config.set_validation_level("warn")
        value = engine.config.get_config_value("section.problems.resource")
    """

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        validation_level: str = ValidationLevel.STRICT,
        environment: Optional[str] = None,
    ):
        """Initialize the InteropEngine

        Args:
            config_dir: Base directory containing configuration files. If None, will search standard locations.
            validation_level: Level of configuration validation (strict, warn, ignore)
            environment: Optional environment to use (development, testing, production)
        """
        # Initialize configuration manager
        self.config = InteropConfigManager(config_dir, validation_level, environment)

        # Initialize template registry
        template_dir = config_dir / "templates"
        self.template_registry = TemplateRegistry(template_dir)

        # Create and register default filters
        default_filters = self._create_default_filters()
        self.template_registry.initialize(default_filters)

        # Component registries for lazy loading
        self._parsers = {}
        self._generators = {}

    # Lazy-loaded parsers
    @cached_property
    def cda_parser(self):
        """Lazily load the CDA parser"""
        return self._get_parser(FormatType.CDA)

    @cached_property
    def hl7v2_parser(self):
        """Lazily load the HL7v2 parser"""
        return self._get_parser(FormatType.HL7V2)

    # Lazy-loaded generators
    @cached_property
    def cda_generator(self):
        """Lazily load the CDA generator"""
        return self._get_generator(FormatType.CDA)

    @cached_property
    def fhir_generator(self):
        """Lazily load the FHIR generator"""
        return self._get_generator(FormatType.FHIR)

    @cached_property
    def hl7v2_generator(self):
        """Lazily load the HL7v2 generator"""
        return self._get_generator(FormatType.HL7V2)

    def _get_parser(self, format_type: FormatType):
        """Get or create a parser for the specified format

        Args:
            format_type: The format type to get a parser for

        Returns:
            The parser instance
        """
        if format_type not in self._parsers:
            if format_type == FormatType.CDA:
                parser = CDAParser(self.config)
                self._parsers[format_type] = parser
            elif format_type == FormatType.HL7V2:
                parser = HL7v2Parser(self.config)
                self._parsers[format_type] = parser
            else:
                raise ValueError(f"Unsupported parser format: {format_type}")

        return self._parsers[format_type]

    def _get_generator(self, format_type: FormatType):
        """Get or create a generator for the specified format

        Args:
            format_type: The format type to get a generator for

        Returns:
            The generator instance
        """
        if format_type not in self._generators:
            if format_type == FormatType.CDA:
                generator = CDAGenerator(self.config, self.template_registry)
                self._generators[format_type] = generator
            elif format_type == FormatType.HL7V2:
                generator = HL7v2Generator(self.config, self.template_registry)
                self._generators[format_type] = generator
            elif format_type == FormatType.FHIR:
                generator = FHIRGenerator(self.config, self.template_registry)
                self._generators[format_type] = generator
            else:
                raise ValueError(f"Unsupported generator format: {format_type}")

        return self._generators[format_type]

    def register_parser(self, format_type: FormatType, parser_instance):
        """Register a custom parser for a format

        Args:
            format_type: The format type to register the parser for
            parser_instance: The parser instance

        Returns:
            Self for method chaining
        """
        self._parsers[format_type] = parser_instance
        return self

    def register_generator(self, format_type: FormatType, generator_instance):
        """Register a custom generator for a format

        Args:
            format_type: The format type to register the generator for
            generator_instance: The generator instance

        Returns:
            Self for method chaining
        """
        self._generators[format_type] = generator_instance
        return self

    def _create_default_filters(self) -> Dict[str, Callable]:
        """Create and return default filter functions for templates

        Returns:
            Dict of filter names to filter functions
        """
        # Get mappings for filter functions
        mappings = self.config.get_mappings()

        # Create filter functions with access to mappings
        def map_system_filter(system, direction="fhir_to_cda"):
            return map_system(system, mappings, direction)

        def map_status_filter(status, direction="fhir_to_cda"):
            return map_status(status, mappings, direction)

        def format_date_filter(date_str, input_format="%Y%m%d", output_format="iso"):
            return format_date(date_str, input_format, output_format)

        def format_timestamp_filter(value=None, format_str="%Y%m%d%H%M%S"):
            return format_timestamp(value, format_str)

        def generate_id_filter(value=None, prefix="hc-"):
            return generate_id(value, prefix)

        def json_filter(obj):
            return to_json(obj)

        def clean_empty_filter(d):
            return clean_empty(d)

        def extract_effective_period_filter(effective_times):
            return extract_effective_period(effective_times)

        def extract_effective_timing_filter(effective_times):
            return extract_effective_timing(effective_times)

        def extract_clinical_status_filter(entry, config):
            return extract_clinical_status(entry, config)

        def extract_reactions_filter(observation, config):
            return extract_reactions(observation, config)

        def map_severity_filter(severity_code, direction="cda_to_fhir"):
            return map_severity(severity_code, mappings, direction)

        # Return dictionary of filters
        return {
            "map_system": map_system_filter,
            "map_status": map_status_filter,
            "format_date": format_date_filter,
            "format_timestamp": format_timestamp_filter,
            "generate_id": generate_id_filter,
            "json": json_filter,
            "clean_empty": clean_empty_filter,
            "extract_effective_period": extract_effective_period_filter,
            "extract_effective_timing": extract_effective_timing_filter,
            "extract_clinical_status": extract_clinical_status_filter,
            "extract_reactions": extract_reactions_filter,
            "map_severity": map_severity_filter,
        }

    def register_template_validator(
        self, resource_type: str, template_model
    ) -> "InteropEngine":
        """Register a custom template validator model for a resource type

        Args:
            resource_type: FHIR resource type (e.g., "Condition", "MedicationStatement")
            template_model: Pydantic model for template validation

        Returns:
            Self for method chaining
        """
        self.config.register_section_template_config(resource_type, template_model)
        return self

    def register_document_validator(
        self, document_type: str, document_model
    ) -> "InteropEngine":
        """Register a custom document validator model for a document type

        Args:
            document_type: Document type (e.g., "ccd", "discharge")
            document_model: Pydantic model for document validation

        Returns:
            Self for method chaining
        """
        self.config.register_document_config(document_type, document_model)
        return self

    def to_fhir(
        self, source_data: str, source_format: Union[str, FormatType]
    ) -> List[Resource]:
        """Convert source format to FHIR resources"""
        format_type = validate_format(source_format)

        if format_type == FormatType.CDA:
            return self._cda_to_fhir(source_data)
        elif format_type == FormatType.HL7V2:
            return self._hl7v2_to_fhir(source_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def from_fhir(
        self,
        resources: List[Resource],
        format_type: Union[str, FormatType],
        **kwargs,
    ) -> str:
        """Convert FHIR resources to HL7v2 or CDA"""
        format_type = validate_format(format_type)

        if format_type == FormatType.HL7V2:
            return self._fhir_to_hl7v2(resources, **kwargs)
        elif format_type == FormatType.CDA:
            return self._fhir_to_cda(resources, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _cda_to_fhir(self, xml: str, **kwargs) -> List[Resource]:
        """Convert CDA XML to FHIR resources

        Args:
            xml: CDA document as XML string
            **kwargs: Additional arguments to pass to parser and generator.

        Returns:
            List[Resource]: List of FHIR resources

        Raises:
            ValueError: If required mappings are missing or if sections are unsupported
        """
        # Get parser and generator (lazy loaded)
        parser = self.cda_parser
        generator = self.fhir_generator

        # Parse sections from CDA XML using the parser
        section_entries = parser.parse_document_sections(xml)

        # Process each section and convert entries to FHIR resources
        resources = []
        for section_key, entries in section_entries.items():
            section_resources = generator.convert_cda_entries_to_resources(
                entries, section_key
            )
            resources.extend(section_resources)

        return resources

    def _fhir_to_cda(
        self, resources: Union[Resource, List[Resource], Bundle], **kwargs
    ) -> str:
        """Convert FHIR resources to CDA XML

        Args:
            resources: A FHIR Bundle, list of resources, or single resource
            **kwargs: Additional arguments to pass to generator.
                     Supported arguments:
                     - document_type: Type of CDA document (e.g. "CCD", "Discharge Summary")

        Returns:
            str: CDA document as XML string

        Raises:
            ValueError: If required mappings are missing or if resource types are unsupported
        """
        # Get generators (lazy loaded)
        cda_generator = self.cda_generator

        # Check for document type
        document_type = kwargs.get("document_type", "ccd")
        if document_type:
            log.info(f"Processing CDA document of type: {document_type}")

        # Get and validate document configuration for this specific document type
        doc_config = self.config.get_document_config(document_type, validate=True)
        if not doc_config:
            raise ValueError(
                f"Invalid or missing document configuration for type: {document_type}"
            )

        # Normalize input to list of resources
        resource_list = normalize_resource_list(resources)

        return cda_generator.generate_document_from_fhir_resources(
            resource_list, document_type
        )

    def _hl7v2_to_fhir(self, source_data: str) -> List[Resource]:
        """Convert HL7v2 to FHIR resources"""
        raise NotImplementedError("HL7v2 to FHIR conversion not implemented")

    def _fhir_to_hl7v2(self, resources: List[Resource]) -> str:
        """Convert FHIR resources to HL7v2"""
        raise NotImplementedError("FHIR to HL7v2 conversion not implemented")
