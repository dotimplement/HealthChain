"""
InteropConfigManager for HealthChain Interoperability Engine

This module provides specialized configuration management for interoperability.
"""

import logging
from typing import Dict, Optional, List, Type

from pydantic import BaseModel

from healthchain.config.base import ConfigManager, ValidationLevel
from healthchain.config.validators import (
    register_cda_document_template_config_model,
    register_cda_section_template_config_model,
    validate_cda_document_config_model,
    validate_cda_section_config_model,
)

log = logging.getLogger(__name__)


class InteropConfigManager(ConfigManager):
    """Specialized configuration manager for the interoperability module

    Extends ConfigManager to handle CDA document and section template configurations.
    Provides functionality for:

    - Loading and validating interop configurations
    - Managing document and section templates
    - Registering custom validation models

    Configuration structure:
    - Document templates (under "document")
    - Section templates (under "sections")
    - Default values and settings

    Validation levels:
    - STRICT: Full validation (default)
    - WARN: Warning-only
    - IGNORE: No validation
    """

    def __init__(
        self,
        config_dir,
        validation_level: str = ValidationLevel.STRICT,
        environment: Optional[str] = None,
    ):
        """Initialize the InteropConfigManager.

        Initializes the configuration manager with the interop module and validates
        the configuration. The interop module configuration must exist in the
        specified config directory.

        Args:
            config_dir: Base directory containing configuration files
            validation_level: Level of validation to perform. Default is STRICT.
                Can be STRICT, WARN, or IGNORE.
            environment: Optional environment name to load environment-specific configs.
                If provided, will load and merge environment-specific configuration.

        Raises:
            ValueError: If the interop module configuration is not found in config_dir.
        """
        # Initialize with "interop" as the fixed module
        super().__init__(config_dir, validation_level, module="interop")
        self.load(environment, skip_validation=True)

        if "interop" not in self._module_configs:
            raise ValueError(
                f"Interop module not found in configuration directory {config_dir}"
            )

        self.validate()

    def _find_cda_sections_config(self) -> Dict:
        """Find CDA section configs in the module configs

        Returns:
            Dict of sections, or empty dict if none found
        """
        return self._find_config_section(module_name="interop", section_name="sections")

    def _find_cda_document_config(self, document_type: str) -> Dict:
        """Find CDA document configuration for a specific document type

        Args:
            document_type: Type of document (e.g., "ccd", "discharge")

        Returns:
            CDA document configuration dict or empty dict if not found
        """
        return self._find_config_section(
            module_name="interop", section_name="document", subsection=document_type
        )

    def _find_cda_document_types(self) -> List[str]:
        """Find available CDA document types in the configs

        Returns:
            List of CDA document type strings
        """
        document_types = []

        # Get top level document section using _find_config_section
        doc_section = self._find_config_section(
            module_name="interop", section_name="document"
        )
        if doc_section:
            document_types.extend(doc_section.keys())

        # Check in subdirectories for additional document types
        # We still need this part as _find_config_section only returns one section/subsection
        for value in self._module_configs["interop"].values():
            if isinstance(value, dict) and "document" in value:
                if (
                    isinstance(value["document"], dict)
                    and value["document"] != doc_section
                ):
                    document_types.extend(value["document"].keys())

        return document_types

    def get_cda_section_configs(self, section_key: Optional[str] = None) -> Dict:
        """Get CDA section configuration(s).

        Retrieves section configurations from the loaded configs. When section_key is provided,
        retrieves configuration for a specific section; otherwise, returns all section configurations.
        Section configurations define how different CDA sections should be processed and mapped to
        FHIR resources.

        Args:
            section_key: Optional section identifier (e.g., "problems", "medications").
                         If provided, returns only that specific section's configuration.

        Returns:
            Dict: Dictionary mapping section keys to their configurations if section_key is None.
                  Single section configuration dict if section_key is provided.

        Raises:
            ValueError: If section_key is provided but not found in configurations
        """
        sections = self._find_cda_sections_config()

        if not sections:
            log.warning("No section configs found")
            return {}

        if section_key is not None:
            if section_key not in sections:
                raise ValueError(f"Section configuration not found: {section_key}")
            return sections[section_key]

        return sections

    def get_cda_document_config(self, document_type: str) -> Dict:
        """Get CDA document configuration for a specific document type.

        Retrieves the configuration for a CDA document type from the loaded configs.
        The configuration contains template settings and other document-specific parameters.

        Args:
            document_type: Type of document (e.g., "ccd", "discharge") to get config for

        Returns:
            Dict containing the document configuration if found, empty dict if not found
            or if document_type is invalid
        """
        document_config = self._find_cda_document_config(document_type)

        if not document_config:
            return {}

        return document_config

    def validate(self) -> bool:
        """Validate that all required configurations are present for the interop module.

        Validates both section and document configurations according to their registered
        validation models. Section configs are required and will cause validation to fail
        if missing or invalid. Document configs are optional but will be validated if present.

        The validation behavior depends on the validation_level setting:
        - IGNORE: Always returns True without validating
        - WARN: Logs warnings for validation failures but returns True
        - ERROR: Returns False if any validation fails

        Returns:
            bool: True if validation passes or is ignored, False if validation fails
                 when validation_level is ERROR
        """
        if self._validation_level == ValidationLevel.IGNORE:
            return True

        is_valid = super().validate()

        # Validate section configs
        section_configs = self._find_cda_sections_config()
        if not section_configs:
            is_valid = self._handle_validation_error("No section configs found")
        else:
            # Validate each section config
            for section_key, section_config in section_configs.items():
                result = validate_cda_section_config_model(section_key, section_config)
                if not result:
                    is_valid = self._handle_validation_error(
                        f"Section config validation failed for key: {section_key}"
                    )

        # Validate document configs - but don't fail if no documents are configured
        # since some use cases might not require documents
        document_types = self._find_cda_document_types()
        for doc_type in document_types:
            doc_config = self._find_cda_document_config(doc_type)
            if doc_config:
                result = validate_cda_document_config_model(doc_type, doc_config)
                if not result:
                    is_valid = self._handle_validation_error(
                        f"Document config validation failed for type: {doc_type}"
                    )

        return is_valid

    def register_cda_section_config(
        self, resource_type: str, config_model: Type[BaseModel]
    ) -> None:
        """Register a validation model for a CDA section configuration.

        Registers a Pydantic model that will be used to validate configuration for a CDA section
        that maps to a specific FHIR resource type. The model defines the required and optional
        fields that should be present in the section configuration.

        Args:
            resource_type: FHIR resource type that the section maps to (e.g. "Condition")
            config_model: Pydantic model class that defines the validation schema for the section config
        """
        register_cda_section_template_config_model(resource_type, config_model)

    def register_cda_document_config(
        self, document_type: str, config_model: Type[BaseModel]
    ) -> None:
        """Register a validation model for a CDA document configuration.

        Registers a Pydantic model that will be used to validate configuration for a CDA document
        type. The model defines the required and optional fields that should be present in the
        document configuration.

        Args:
            document_type: Document type identifier (e.g., "ccd", "discharge")
            config_model: Pydantic model class that defines the validation schema for the document config
        """
        register_cda_document_template_config_model(document_type, config_model)
