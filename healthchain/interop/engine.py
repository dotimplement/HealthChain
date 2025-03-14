import logging
from functools import cached_property

from enum import Enum
from typing import Dict, List, Union, Optional, Callable, Any, Set
from pathlib import Path

from fhir.resources.resource import Resource

from .parsers.cda import CDAParser
from .parsers.hl7v2 import HL7v2Parser
from .filters import (
    format_date,
    map_system,
    map_status,
    clean_empty,
    format_timestamp,
    generate_id,
    to_json,
)
from .config_manager import ConfigManager, ValidationLevel
from .template_registry import TemplateRegistry
from .converters import fhir as fhir_utils
from .generators.cda import CDAGenerator
from .generators.fhir import FHIRGenerator
from .generators.hl7v2 import HL7v2Generator

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
    """Generic interoperability engine for converting between healthcare formats"""

    def __init__(
        self,
        config_dir: Path,
        validation_level: str = ValidationLevel.STRICT,
        environment: Optional[str] = None,
    ):
        """Initialize the InteropEngine

        Args:
            config_dir: Base directory containing configuration files
            validation_level: Level of configuration validation (strict, warn, ignore)
            environment: Optional environment to use (development, testing, production)
        """
        # Initialize configuration manager
        self.config_dir = config_dir
        self.config_manager = ConfigManager(config_dir, validation_level)
        self.config_manager.load(environment)

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
                parser = CDAParser(self.config_manager)
                self._parsers[format_type] = parser
            elif format_type == FormatType.HL7V2:
                parser = HL7v2Parser(self.config_manager)
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
                generator = CDAGenerator(self.config_manager, self.template_registry)
                self._generators[format_type] = generator
            elif format_type == FormatType.HL7V2:
                generator = HL7v2Generator(self.config_manager, self.template_registry)
                self._generators[format_type] = generator
            elif format_type == FormatType.FHIR:
                generator = FHIRGenerator(self.config_manager, self.template_registry)
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

    def register_config_schema(
        self, config_type: str, required_keys: Set[str]
    ) -> "InteropEngine":
        """Register a custom configuration schema for validation

        Args:
            config_type: Type of configuration (e.g., "section", "document")
            required_keys: Set of required keys for this configuration type

        Returns:
            Self for method chaining
        """
        self.config_manager.register_schema(config_type, required_keys)
        return self

    def set_validation_level(self, level: str) -> "InteropEngine":
        """Set the configuration validation level

        Args:
            level: Validation level (strict, warn, ignore)

        Returns:
            Self for method chaining
        """
        self.config_manager.set_validation_level(level)
        return self

    def get_environment(self) -> str:
        """Get the current environment

        Returns:
            String representing the current environment
        """
        return self.config_manager.get_environment()

    def set_environment(self, environment: str) -> "InteropEngine":
        """Set the environment and reload environment-specific configuration

        Args:
            environment: Environment to set (development, testing, production)

        Returns:
            Self for method chaining
        """
        self.config_manager.set_environment(environment)
        return self

    def get_config_value(self, path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation path

        Args:
            path: Dot notation path (e.g., "section.problems.resource")
            default: Default value if path not found

        Returns:
            Configuration value or default
        """
        return self.config_manager.get_config_value(path, default)

    def get_loaded_defaults(self) -> Dict:
        """Get all loaded default values

        Returns:
            Dictionary of default values loaded from defaults.yaml
        """
        return self.config_manager.get_defaults()

    def is_defaults_loaded(self) -> bool:
        """Check if the defaults.yaml file is loaded

        Returns:
            True if defaults.yaml is loaded, False otherwise
        """
        defaults = self.get_loaded_defaults()
        return bool(defaults)

    def _create_default_filters(self) -> Dict[str, Callable]:
        """Create and return default filter functions for templates

        Returns:
            Dict of filter names to filter functions
        """
        # Get mappings for filter functions
        mappings = self.config_manager.get_mappings()

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

        # Return dictionary of filters
        return {
            "map_system": map_system_filter,
            "map_status": map_status_filter,
            "format_date": format_date_filter,
            "format_timestamp": format_timestamp_filter,
            "generate_id": generate_id_filter,
            "json": json_filter,
            "clean_empty": clean_empty_filter,
        }

    def add_filter(self, name: str, filter_func: Callable) -> "InteropEngine":
        """Add a custom filter function to the template engine

        Args:
            name: Name of the filter to use in templates
            filter_func: Filter function to register

        Returns:
            Self for method chaining
        """
        self.template_registry.add_filter(name, filter_func)
        return self

    def add_filters(self, filters: Dict[str, Callable]) -> "InteropEngine":
        """Add multiple custom filter functions to the template engine

        Args:
            filters: Dictionary of filter names to filter functions

        Returns:
            Self for method chaining
        """
        self.template_registry.add_filters(filters)
        return self

    def get_filter(self, name: str) -> Optional[Callable]:
        """Get a registered filter function by name

        Args:
            name: Name of the filter

        Returns:
            The filter function or None if not found
        """
        return self.template_registry.get_filter(name)

    def get_filters(self) -> Dict[str, Callable]:
        """Get all registered filter functions

        Returns:
            Dictionary of filter names to filter functions
        """
        return self.template_registry.get_filters()

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
    ) -> str:
        """Convert FHIR resources to HL7v2 or CDA"""
        format_type = validate_format(format_type)

        if format_type == FormatType.HL7V2:
            return self._fhir_to_hl7v2(resources)
        elif format_type == FormatType.CDA:
            return self._fhir_to_cda(resources)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _cda_to_fhir(self, source_data: str) -> List[Resource]:
        """Convert CDA XML to FHIR resources

        Args:
            source_data: CDA document as XML string

        Returns:
            List[Resource]: List of FHIR resources

        Raises:
            ValueError: If required mappings are missing or if sections are unsupported
        """
        # Get required configurations
        section_configs = self.config_manager.get_section_configs()

        if not section_configs:
            raise ValueError("No section configs found in configs/cda/section.yaml")

        # Get parser and generator (lazy loaded)
        parser = self.cda_parser
        generator = self.fhir_generator

        # Parse sections from CDA XML using the parser
        section_entries = parser.parse_document(source_data)

        # Process each section and convert entries to FHIR resources
        resources = []
        for section_key, entries in section_entries.items():
            # Get resource type from section config
            resource_type = self.config_manager.get_config_value(
                f"sections.{section_key}.resource", None
            )
            if not resource_type:
                log.warning(f"No resource type specified for section {section_key}")
                continue

            # Convert entries to resource dictionaries using the generator
            resource_dicts = generator.convert_entries_to_resources(
                entries, section_key, resource_type
            )

            # Convert resource dictionaries to FHIR resources using the utility functions
            section_resources = fhir_utils.convert_resource_dicts_to_resources(
                resource_dicts, resource_type, self.config_manager
            )
            resources.extend(section_resources)

        return resources

    def _fhir_to_cda(self, resources: Union[Resource, List[Resource]]) -> str:
        """Convert FHIR resources to CDA XML

        Args:
            resources: A FHIR Bundle, list of resources, or single resource

        Returns:
            str: CDA document as XML string

        Raises:
            ValueError: If required mappings are missing or if resource types are unsupported
        """
        # Get generators (lazy loaded)
        cda_generator = self.cda_generator

        # Normalize input to list of resources
        resource_list = fhir_utils.normalize_resources(resources)

        # Process resources and group by section
        section_entries = {}
        for resource in resource_list:
            resource_type = resource.__class__.__name__

            # Find matching section for resource type using utility function
            section_key = fhir_utils.find_section_for_resource_type(
                resource_type, self.config_manager
            )
            if not section_key:
                continue

            # Get template name for this section
            template_name = cda_generator.get_section_template_name(
                section_key, "entry"
            )
            if not template_name:
                continue

            # Render entry using template
            entry = cda_generator.render_entry(resource, section_key, template_name)
            if entry:
                section_entries.setdefault(section_key, []).append(entry)

        # Generate the complete CDA document using the simplified method
        return cda_generator.generate_document_from_resources(
            resources, section_entries
        )

    def _hl7v2_to_fhir(self, source_data: str) -> List[Resource]:
        """Convert HL7v2 to FHIR resources"""
        raise NotImplementedError("HL7v2 to FHIR conversion not implemented")

    def _fhir_to_hl7v2(self, resources: List[Resource]) -> str:
        """Convert FHIR resources to HL7v2"""
        raise NotImplementedError("FHIR to HL7v2 conversion not implemented")
