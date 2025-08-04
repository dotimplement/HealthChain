import logging

from functools import cached_property
from typing import List, Union, Optional, Any
from pathlib import Path

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle
from pydantic import BaseModel

from healthchain.config.base import ValidationLevel
from healthchain.interop.config_manager import InteropConfigManager
from healthchain.interop.generators.base import BaseGenerator
from healthchain.interop.parsers.base import BaseParser
from healthchain.interop.types import FormatType, validate_format

from healthchain.interop.parsers.cda import CDAParser
from healthchain.interop.template_registry import TemplateRegistry
from healthchain.interop.generators.cda import CDAGenerator
from healthchain.interop.generators.fhir import FHIRGenerator
from healthchain.interop.filters import create_default_filters

log = logging.getLogger(__name__)


def normalize_resource_list(
    resources: Union[Resource, List[Resource], Bundle],
) -> List[Resource]:
    """Convert input resources to a normalized list format"""
    if isinstance(resources, Bundle):
        return [entry.resource for entry in resources.entry if entry.resource]
    elif isinstance(resources, list):
        return resources
    else:
        return [resources]


class InteropEngine:
    """Generic interoperability engine for converting between healthcare formats

    The InteropEngine provides capabilities for converting between different
    healthcare data format standards, such as HL7 FHIR, CDA, and HL7v2.

    The engine uses a template-based approach for transformations, with templates
    stored in the configured template directory. Transformations are handled by
    format-specific parsers and generators that are lazily loaded as needed.

    Configuration is handled through the `config` property, which provides
    direct access to the underlying ConfigManager instance. This allows
    for setting validation levels, changing environments, and accessing
    configuration values.

    The engine supports registering custom parsers, generators, and validators
    to extend or override the default functionality.

    Example:
        engine = InteropEngine()

        # Convert CDA to FHIR
        fhir_resources = engine.to_fhir(cda_xml, src_format="cda")

        # Convert FHIR to CDA
        cda_xml = engine.from_fhir(fhir_resources, dest_format="cda")

        # Access config directly:
        engine.config.set_environment("production")
        engine.config.set_validation_level("warn")
        value = engine.config.get_config_value("cda.sections.problems.resource")

        # Access the template registry:
        template = engine.template_registry.get_template("cda_fhir/condition")
        engine.template_registry.add_filter()

        # Register custom components:
        engine.register_parser(FormatType.CDA, custom_parser)
        engine.register_generator(FormatType.FHIR, custom_generator)

        # Register custom configuration validators:
        engine.register_cda_section_config_validator("Procedure", ProcedureSectionConfig)
        engine.register_cda_document_config_validator("CCD", CCDDocumentConfig)
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
        # Get required configuration for filters
        mappings_dir = self.config.get_config_value("defaults.mappings_dir")
        if not mappings_dir:
            log.warning("No mappings directory configured, using default mappings")
            mappings_dir = "cda_default"
        mappings = self.config.get_mappings(mappings_dir)
        id_prefix = self.config.get_config_value("defaults.common.id_prefix")

        # Get default filters from the filters module
        default_filters = create_default_filters(mappings, id_prefix)
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
            format_type: The format type to get a parser for (CDA or HL7v2)

        Returns:
            The parser instance for the specified format

        Raises:
            ValueError: If an unsupported format type is provided
        """
        if format_type not in self._parsers:
            if format_type == FormatType.CDA:
                parser = CDAParser(self.config)
                self._parsers[format_type] = parser
            elif format_type == FormatType.HL7V2:
                raise NotImplementedError("HL7v2 parser not implemented")
            else:
                raise ValueError(f"Unsupported parser format: {format_type}")

        return self._parsers[format_type]

    def _get_generator(self, format_type: FormatType):
        """Get or create a generator for the specified format

        Args:
            format_type: The format type to get a generator for (CDA, HL7v2, or FHIR)

        Returns:
            The generator instance for the specified format

        Raises:
            ValueError: If an unsupported format type is provided
        """
        if format_type not in self._generators:
            if format_type == FormatType.CDA:
                generator = CDAGenerator(self.config, self.template_registry)
                self._generators[format_type] = generator
            elif format_type == FormatType.HL7V2:
                raise NotImplementedError("HL7v2 generator not implemented")
            elif format_type == FormatType.FHIR:
                generator = FHIRGenerator(self.config, self.template_registry)
                self._generators[format_type] = generator
            else:
                raise ValueError(f"Unsupported generator format: {format_type}")

        return self._generators[format_type]

    def register_parser(
        self, format_type: FormatType, parser_instance: BaseParser
    ) -> "InteropEngine":
        """Register a custom parser for a format type. This will replace the default parser for the format type.

        Args:
            format_type: The format type (CDA, HL7v2) to register the parser for
            parser_instance: The parser instance that implements the parsing logic

        Returns:
            InteropEngine: Returns self for method chaining

        Example:
            engine.register_parser(FormatType.CDA, CustomCDAParser())
        """
        self._parsers[format_type] = parser_instance
        return self

    def register_generator(
        self, format_type: FormatType, generator_instance: BaseGenerator
    ) -> "InteropEngine":
        """Register a custom generator for a format type. This will replace the default generator for the format type.

        Args:
            format_type: The format type (CDA, HL7v2, FHIR) to register the generator for
            generator_instance: The generator instance that implements the generation logic

        Returns:
            InteropEngine: Returns self for method chaining

        Example:
            engine.register_generator(FormatType.CDA, CustomCDAGenerator())
        """
        self._generators[format_type] = generator_instance
        return self

    # TODO: make the config validator functions more generic
    def register_cda_section_config_validator(
        self, resource_type: str, template_model: BaseModel
    ) -> "InteropEngine":
        """Register a custom section config validator model for a resource type

        Args:
            resource_type: FHIR resource type (e.g., "Condition", "MedicationStatement") which converts to the CDA section
            template_model: Pydantic model for CDA section config validation

        Returns:
            Self for method chaining

        Example:
            # Register a config validator for the Problem section, which is converted from the Condition resource
            engine.register_cda_section_config_validator(
                "Condition", ProblemSectionConfig
            )
        """
        self.config.register_cda_section_config(resource_type, template_model)
        return self

    def register_cda_document_config_validator(
        self, document_type: str, document_model: BaseModel
    ) -> "InteropEngine":
        """Register a custom document validator model for a document type

        Args:
            document_type: Document type (e.g., "ccd", "discharge")
            document_model: Pydantic model for document validation

        Returns:
            Self for method chaining

        Example:
            # Register a config validator for the CCD document type
            engine.register_cda_document_validator(
                "ccd", CCDDocumentConfig
            )
        """
        self.config.register_cda_document_config(document_type, document_model)
        return self

    def to_fhir(
        self, src_data: str, src_format: Union[str, FormatType]
    ) -> List[Resource]:
        """Convert source data to FHIR resources

        Args:
            src_data: Input data as string (CDA XML or HL7v2 message)
            src_format: Source format type, either as string ("cda", "hl7v2")
                         or FormatType enum

        Returns:
            List[Resource]: List of FHIR resources generated from the source data

        Raises:
            ValueError: If src_format is not supported

        Example:
            # Convert CDA XML to FHIR resources
            fhir_resources = engine.to_fhir(cda_xml, src_format="cda")
        """
        src_format = validate_format(src_format)

        if src_format == FormatType.CDA:
            return self._cda_to_fhir(src_data)
        elif src_format == FormatType.HL7V2:
            return self._hl7v2_to_fhir(src_data)
        else:
            raise ValueError(f"Unsupported format: {src_format}")

    def from_fhir(
        self,
        resources: Union[List[Resource], Bundle],
        dest_format: Union[str, FormatType],
        **kwargs: Any,
    ) -> str:
        """Convert FHIR resources to a target format

        Args:
            resources: List of FHIR resources to convert or a FHIR Bundle
            dest_format: Destination format type, either as string ("cda", "hl7v2")
                        or FormatType enum
            **kwargs: Additional arguments to pass to generator.
                     For CDA: document_type (str) - Type of CDA document (e.g. "ccd", "discharge")

        Returns:
            str: Converted data as string (CDA XML or HL7v2 message)

        Raises:
            ValueError: If dest_format is not supported

        Example:
            # Convert FHIR resources to CDA XML
            cda_xml = engine.from_fhir(fhir_resources, dest_format="cda")
        """
        dest_format = validate_format(dest_format)
        resources = normalize_resource_list(resources)

        if dest_format == FormatType.HL7V2:
            return self._fhir_to_hl7v2(resources, **kwargs)
        elif dest_format == FormatType.CDA:
            return self._fhir_to_cda(resources, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {dest_format}")

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
        section_entries = parser.from_string(xml)

        # Process each section and convert entries to FHIR resources
        resources = []
        for section_key, entries in section_entries.items():
            section_resources = generator.transform(
                entries, src_format=FormatType.CDA, section_key=section_key
            )
            resources.extend(section_resources)

        return resources

    def _fhir_to_cda(self, resources: List[Resource], **kwargs) -> str:
        """Convert FHIR resources to CDA XML

        Args:
            resources: A list of FHIR resources
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

        # Get document configuration for this specific document type
        doc_config = self.config.get_cda_document_config(document_type)
        if not doc_config:
            raise ValueError(
                f"Invalid or missing document configuration for type: {document_type}"
            )

        return cda_generator.transform(resources, document_type=document_type)

    def _hl7v2_to_fhir(self, source_data: str) -> List[Resource]:
        """Convert HL7v2 to FHIR resources"""
        parser = self.hl7v2_parser
        generator = self.fhir_generator

        # Parse HL7v2 message using the parser
        message_entries = parser.from_string(source_data)

        # Process each message entry and convert to FHIR resources
        resources = []
        for message_key, entries in message_entries.items():
            resource_entries = generator.transform(
                entries, src_format=FormatType.HL7V2, message_key=message_key
            )
            resources.extend(resource_entries)

        return resources

    def _fhir_to_hl7v2(self, resources: List[Resource]) -> str:
        """Convert FHIR resources to HL7v2"""
        generator = self.hl7v2_generator

        # Process each resource and convert to HL7v2 message
        messages = []
        for resource in resources:
            message = generator.transform(resource)
            messages.append(message)

        return messages
