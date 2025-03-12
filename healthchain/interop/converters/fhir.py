"""
FHIR Converter for HealthChain Interoperability Engine

This module provides functionality for converting to and from FHIR resources.
"""

import logging
import importlib
import uuid
from typing import Dict, List, Optional, Union
from pathlib import Path

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle

log = logging.getLogger(__name__)


class FHIRConverter:
    """Handles conversion to and from FHIR resources"""

    def __init__(self, config_manager):
        """Initialize the FHIR converter

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.template_registry = None
        self.parser = None

    def set_template_registry(self, template_registry):
        """Set the template registry

        Args:
            template_registry: Template registry instance
        """
        self.template_registry = template_registry
        return self

    def set_parser(self, parser):
        """Set the parser

        Args:
            parser: Parser instance
        """
        self.parser = parser
        return self

    def _create_fhir_resource_from_dict(
        self, resource_dict: Dict, resource_type: str
    ) -> Optional[Resource]:
        """Create a FHIR resource instance from a dictionary

        Args:
            resource_dict: Dictionary representation of the resource
            resource_type: Type of FHIR resource to create

        Returns:
            Optional[Resource]: FHIR resource instance or None if creation failed
        """
        try:
            resource_module = importlib.import_module(
                f"fhir.resources.{resource_type.lower()}"
            )
            resource_class = getattr(resource_module, resource_type)
            return resource_class(**resource_dict)
        except Exception as e:
            log.error(f"Failed to create FHIR resource: {str(e)}")
            return None

    def add_required_fields(self, resource_dict: Dict, resource_type: str):
        """Add required fields to resource dictionary based on type

        Args:
            resource_dict: Dictionary representation of the resource
            resource_type: Type of FHIR resource
        """
        # Add common fields
        id_prefix = self.config_manager.get_config_value(
            "defaults.common.id_prefix", "hc-"
        )
        if "id" not in resource_dict:
            resource_dict["id"] = f"{id_prefix}{str(uuid.uuid4())}"

        # Get default values from configuration if available
        default_subject = self.config_manager.get_config_value(
            "defaults.common.subject", {"reference": "Patient/example"}
        )
        if "subject" not in resource_dict:
            resource_dict["subject"] = default_subject

        # Add resource-specific required fields
        if resource_type == "Condition":
            if "clinicalStatus" not in resource_dict:
                default_status = self.config_manager.get_config_value(
                    "defaults.resources.Condition.clinicalStatus",
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "unknown",
                            }
                        ]
                    },
                )
                resource_dict["clinicalStatus"] = default_status
        elif resource_type == "MedicationStatement":
            if "status" not in resource_dict:
                default_status = self.config_manager.get_config_value(
                    "defaults.resources.MedicationStatement.status", "unknown"
                )
                resource_dict["status"] = default_status
        elif resource_type == "AllergyIntolerance":
            if "clinicalStatus" not in resource_dict:
                default_status = self.config_manager.get_config_value(
                    "defaults.resources.AllergyIntolerance.clinicalStatus",
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                "code": "unknown",
                            }
                        ]
                    },
                )
                resource_dict["clinicalStatus"] = default_status

    def normalize_resources(
        self, resources: Union[Resource, List[Resource], Bundle]
    ) -> List[Resource]:
        """Convert input resources to a normalized list format

        Args:
            resources: A FHIR Bundle, list of resources, or single resource

        Returns:
            List of FHIR resources
        """
        if isinstance(resources, Bundle):
            return [entry.resource for entry in resources.entry if entry.resource]
        elif isinstance(resources, list):
            return resources
        else:
            return [resources]

    def convert_cda_entries_to_fhir_resources(
        self, section_entries: Dict, section_configs: Dict
    ) -> List[Resource]:
        """Convert CDA section entries to FHIR resources

        Args:
            section_entries: Dictionary mapping section keys to lists of entry dictionaries
            section_configs: Configuration for all sections

        Returns:
            List of FHIR resources
        """
        if not self.template_registry or not self.parser:
            raise ValueError(
                "Template registry and parser must be set before conversion"
            )

        resources = []

        for section_key, entries in section_entries.items():
            if section_key not in section_configs:
                log.warning(f"No configuration found for section: {section_key}")
                continue

            section_config = section_configs[section_key]
            template_key = Path(section_config.get("resource_template", "")).stem

            if not template_key:
                log.warning(
                    f"No resource template specified for section: {section_key}"
                )
                continue

            if not self.template_registry.has_template(template_key):
                log.warning(
                    f"Template {template_key} not found, skipping section {section_key}"
                )
                continue

            template = self.template_registry.get_template(template_key)

            # Process each entry in the section
            section_resources = self._convert_cda_entries_to_fhir(
                entries, template, section_config, section_key
            )
            resources.extend(section_resources)

        return resources

    def convert_fhir_to_cda_entries(
        self, resources: List[Resource], section_configs: Dict, cda_generator
    ) -> Dict:
        """Process resources and group them by section with rendered entries

        Args:
            resources: List of FHIR resources
            section_configs: Configuration for all sections
            cda_generator: CDA generator instance for rendering entries

        Returns:
            Dictionary mapping section keys to lists of entry dictionaries
        """
        if not self.template_registry:
            raise ValueError(
                "Template registry must be set before processing resources"
            )

        section_entries = {}

        for resource in resources:
            # Find matching section for resource type
            section_key = self._find_section_for_fhir_resource(
                resource, section_configs
            )

            if not section_key:
                continue

            # Get template for this section
            template_name = Path(
                section_configs[section_key].get("entry_template", "")
            ).stem
            if not self.template_registry.has_template(template_name):
                log.warning(
                    f"Template {template_name} not found, skipping section {section_key}"
                )
                continue

            # Render entry using template
            entry = cda_generator.render_entry(
                resource, section_key, template_name, section_configs[section_key]
            )
            if entry:
                section_entries.setdefault(section_key, []).append(entry)

        return section_entries

    def _find_section_for_fhir_resource(
        self, resource: Resource, section_configs: Dict
    ) -> Optional[str]:
        """Find the appropriate section key for a given resource

        Args:
            resource: FHIR resource
            section_configs: Configuration for all sections

        Returns:
            Section key or None if no matching section found
        """
        resource_type = resource.__class__.__name__

        # Find matching section for resource type
        section_key = next(
            (
                key
                for key, config in section_configs.items()
                if config.get("resource") == resource_type
            ),
            None,
        )

        if not section_key:
            log.warning(f"Unsupported resource type: {resource_type}")

        return section_key

    def _convert_cda_entries_to_fhir(
        self, entries: List[Dict], template, section_config: Dict, section_key: str
    ) -> List[Resource]:
        """Process entries from a single section and convert to FHIR resources

        Args:
            entries: List of entries from a section
            template: The template to use for rendering
            section_config: Configuration for the section
            section_key: Key identifying the section

        Returns:
            List[Resource]: List of FHIR resources from this section
        """
        resources = []
        resource_type = section_config.get("resource")

        if not resource_type:
            log.error(f"Missing resource type in section config for {section_key}")
            return resources

        for entry in entries:
            try:
                # Convert entry to FHIR resource dictionary using the parser
                resource_dict = self.parser.render_fhir_resource_from_cda_entry(
                    entry, template, section_config
                )

                # Add required fields based on resource type
                self.add_required_fields(resource_dict, resource_type)

                # Create FHIR resource instance
                resource = self._create_fhir_resource_from_dict(
                    resource_dict, resource_type
                )
                if resource:
                    resources.append(resource)

            except Exception as e:
                log.error(f"Failed to convert entry in section {section_key}: {str(e)}")
                continue

        return resources
