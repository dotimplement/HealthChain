"""
FHIR Generator for HealthChain Interoperability Engine

This module provides functionality for generating FHIR resources from templates.
"""

import uuid
import logging
from typing import Dict, List, Optional

from fhir.resources.resource import Resource

from healthchain.interop.template_renderer import TemplateRenderer
from healthchain.interop.utils import create_resource

log = logging.getLogger(__name__)


class FHIRGenerator(TemplateRenderer):
    """Handles generation of FHIR resources from templates"""

    def render_resource_from_entry(
        self, entry: Dict, section_key: str, template=None
    ) -> Optional[Dict]:
        """
        Process an entry using a template and prepare it for FHIR conversion

        Args:
            entry: The entry data dictionary
            section_key: Key identifying the section
            template: Optional template to use (if not provided, will be retrieved from section config)

        Returns:
            Dict: Processed resource dictionary ready for FHIR conversion
        """
        try:
            # Get template if not provided
            if template is None:
                template = self.get_section_template(section_key, "resource")
                if not template:
                    log.error(f"No resource template found for section {section_key}")
                    return None

            # Get section configuration
            section_config = self.get_section_config(section_key)

            # Create context with entry data and config
            context = {"entry": entry, "config": section_config}

            # Add rendering options to context if available
            rendering = self.config_manager.get_config_value(
                f"sections.{section_key}.rendering", {}
            )
            if rendering:
                context["rendering"] = rendering

            # Render template with context
            return self.render_template(template, context)

        except Exception as e:
            log.error(f"Failed to render resource for section {section_key}: {str(e)}")
            return None

    def convert_cda_entries_to_resources(
        self, entries: List[Dict], section_key: str
    ) -> List[Dict]:
        """
        Convert entries from a section to FHIR resource dictionaries

        Args:
            entries: List of entries from a section
            section_key: Key identifying the section

        Returns:
            List of FHIR resource dictionaries
        """
        resources = []
        template = self.get_section_template(section_key, "resource")

        if not template:
            log.error(f"No resource template found for section {section_key}")
            return resources

        resource_type = self.config_manager.get_config_value(
            f"sections.{section_key}.resource", None
        )
        if not resource_type:
            log.warning(f"No resource type specified for section {section_key}")
            return resources

        for entry in entries:
            try:
                # Convert entry to FHIR resource dictionary
                resource_dict = self.render_resource_from_entry(
                    entry, section_key, template
                )
                if not resource_dict:
                    continue

                resource = self._validate_fhir_resource(resource_dict, resource_type)

                if resource:
                    resources.append(resource)

            except Exception as e:
                log.error(f"Failed to convert entry in section {section_key}: {str(e)}")
                continue

        return resources

    def _validate_fhir_resource(
        self, resource_dict: Dict, resource_type: str
    ) -> Optional[Resource]:
        """Validate a FHIR resource dictionary

        Args:
            resource_dict: Dictionary representation of the resource
            resource_type: Type of FHIR resource to create
            config_manager: Configuration manager instance

        Returns:
            Optional[Resource]: FHIR resource instance or None if validation failed
        """

        try:
            resource_dict = self._add_required_fields(resource_dict, resource_type)
            resource = create_resource(resource_dict, resource_type)
            if resource:
                return resource
        except Exception as e:
            log.error(f"Failed to validate FHIR resource: {str(e)}")
            return None

    def _add_required_fields(self, resource_dict: Dict, resource_type: str) -> Dict:
        """Add required fields to resource dictionary based on type

        Args:
            resource_dict: Dictionary representation of the resource
            resource_type: Type of FHIR resource
            config_manager: Configuration manager instance

        Returns:
            Dict: The resource dictionary with required fields added
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

        return resource_dict
