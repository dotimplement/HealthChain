"""
InteropConfigManager for HealthChain Interoperability Engine

This module provides specialized configuration management for interoperability.
"""

import logging
from typing import Dict, Optional, List

from healthchain.config.base import ConfigManager, ValidationLevel
from healthchain.config.validators import (
    register_document_config_model,
    register_template_config_model,
    validate_document_config_model,
    validate_section_config_model,
)

log = logging.getLogger(__name__)


class InteropConfigManager(ConfigManager):
    """Specialized configuration manager for the interoperability module"""

    def __init__(
        self,
        config_dir,
        validation_level: str = ValidationLevel.STRICT,
        environment: Optional[str] = None,
    ):
        """Initialize the InteropConfigManager

        Args:
            config_dir: Base directory containing configuration files
            validation_level: Level of validation to perform
            environment: Optional environment to use
        """
        # Initialize with "interop" as the fixed module
        super().__init__(config_dir, validation_level, module="interop")
        self.load(environment)

        if "interop" not in self._module_configs:
            raise ValueError(
                f"Interop module not found in configuration directory {config_dir}"
            )

    def _find_sections_config(self) -> Dict:
        """Find section configs in the module configs

        Returns:
            Dict of sections, or empty dict if none found
        """
        return self._find_config_section(module_name="interop", section_name="sections")

    def _find_document_config(self, document_type: str) -> Dict:
        """Find document configuration for a specific document type

        Args:
            document_type: Type of document (e.g., "ccd", "discharge")

        Returns:
            Document configuration dict or empty dict if not found
        """
        return self._find_config_section(
            module_name="interop", section_name="document", subsection=document_type
        )

    def _find_document_types(self) -> List[str]:
        """Find available document types in the configs

        Returns:
            List of document type strings
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

    def get_section_configs(self, validate: bool = False) -> Dict:
        """Get section configurations, optionally validating them

        Args:
            validate: Whether to validate the configurations

        Returns:
            Dict of section configurations
        """
        sections = self._find_sections_config()

        if not sections:
            log.warning("No section configs found")
            return {}

        if not validate:
            return sections

        # Validate if requested
        validated_sections = {}
        for section_key, section_config in sections.items():
            result = validate_section_config_model(section_key, section_config)
            if result or self._validation_level != ValidationLevel.STRICT:
                validated_sections[section_key] = section_config

        return validated_sections

    def get_document_config(self, document_type: str, validate: bool = False) -> Dict:
        """Get document configuration for a specific document type

        Args:
            document_type: Type of document (e.g., "ccd", "discharge")
            validate: Whether to validate the configuration

        Returns:
            Document configuration dict or empty dict if not found or validation failed
        """
        document_config = self._find_document_config(document_type)

        if not document_config:
            return {}

        if not validate:
            return document_config

        # Validate if requested
        result = validate_document_config_model(document_type, document_config)
        if not result and self._validation_level == ValidationLevel.STRICT:
            self._handle_validation_error(
                f"Document config validation failed for type: {document_type}"
            )
            return {}

        return document_config

    def validate(self) -> bool:
        """Validate that all required configurations are present for the interop module"""
        is_valid = super().validate()

        # Validate section configs
        section_configs = self.get_section_configs(validate=True)
        if not section_configs:
            is_valid = self._handle_validation_error("No section configs found")

        # Validate document configs - but don't fail if no documents are configured
        # since some use cases might not require documents
        document_types = self._find_document_types()
        for doc_type in document_types:
            if not self.get_document_config(doc_type, validate=True):
                is_valid = False

        return is_valid

    def register_section_template_config(
        self, resource_type: str, template_model
    ) -> None:
        """Register a custom template model

        Args:
            resource_type: FHIR resource type
            template_model: Pydantic model for corresponding section template validation
        """
        register_template_config_model(resource_type, template_model)

    def register_document_config(self, document_type: str, document_model) -> None:
        """Register a custom document model

        Args:
            document_type: Document type (e.g., "ccd", "discharge")
            document_model: Pydantic model for document validation
        """
        register_document_config_model(document_type, document_model)
