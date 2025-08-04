"""
FHIR Generator for HealthChain Interoperability Engine

This module provides functionality for generating FHIR resources from templates.
"""

import uuid
import logging
from typing import Dict, List, Optional, Type, Any

from fhir.resources.resource import Resource
from liquid import Template

from healthchain.interop.generators.base import BaseGenerator
from healthchain.fhir import create_resource_from_dict
from healthchain.interop.types import FormatType


log = logging.getLogger(__name__)


class FHIRGenerator(BaseGenerator):
    """Handles generation of FHIR resources from templates.

    This class provides functionality to convert CDA section entries into FHIR resources
    using configurable templates. It handles validation, required field population, and
    error handling during the conversion process.

    Key features:
    - Template-based conversion of CDA entries (xmltodict format) to FHIR resources
    - Automatic population of required FHIR fields based on configuration for
        common resource types like Condition, MedicationStatement, AllergyIntolerance
    - Validation of generated FHIR resources

    Example:
        generator = FHIRGenerator(config_manager, template_registry)

        # Convert CDA problem entries to FHIR Condition resources
        problems = generator.generate_resources_from_cda_section_entries(
            entries=problem_entries,
            section_key="problems"  # from configs
        )
    """

    def transform(self, data: List[Dict], **kwargs: Any) -> List[Resource]:
        """Transform input data to FHIR resources.

        Args:
            data: List of entries from source format
            **kwargs:
                src_format: The source format type (FormatType.CDA or FormatType.HL7V2)
                section_key: For CDA, the section key
                message_key: For HL7v2, the message key

        Returns:
            List[Resource]: FHIR resources
        """
        src_format = kwargs.get("src_format")
        if src_format == FormatType.CDA:
            return self.generate_resources_from_cda_section_entries(
                data, kwargs.get("section_key")
            )
        elif src_format == FormatType.HL7V2:
            return self.generate_resources_from_hl7v2_entries(
                data, kwargs.get("message_key")
            )
        else:
            raise ValueError(f"Unsupported source format: {src_format}")

    def generate_resources_from_cda_section_entries(
        self, entries: List[Dict], section_key: str
    ) -> List[Dict]:
        """
        Convert CDA section entries into FHIR resources using configured templates.

        This method processes entries from a CDA section and generates corresponding FHIR
        resources based on templates and configuration. It handles validation and error
        checking during the conversion process.

        Args:
            entries: List of CDA section entries in xmltodict format to convert
            section_key: Configuration key identifying the section (e.g. "problems", "medications")
                Used to look up templates and resource type mappings

        Returns:
            List of validated FHIR resource dictionaries. Empty list if conversion fails.

        Example:
            # Convert problem list entries to FHIR Condition resources
            conditions = generator.generate_resources_from_cda_section_entries(
                problem_entries, "problems"
            )
        """
        if not section_key:
            log.error(
                "No section key provided for CDA section entries: data needs to be in the format \
                      '{<section_key>}: {<section_entries>}'"
            )
            return []

        resources = []
        template = self.get_template_from_section_config(section_key, "resource")

        if not template:
            log.error(f"No resource template found for section {section_key}")
            return resources

        resource_type = self.config.get_config_value(
            f"cda.sections.{section_key}.resource"
        )
        if not resource_type:
            log.error(f"No resource type specified for section {section_key}")
            return resources

        for entry in entries:
            try:
                # Convert entry to FHIR resource dictionary
                resource_dict = self._render_resource_from_entry(
                    entry, section_key, template
                )
                if not resource_dict:
                    continue

                log.debug(f"Rendered FHIR resource: {resource_dict}")

                resource = self._validate_fhir_resource(resource_dict, resource_type)

                if resource:
                    resources.append(resource)

            except Exception as e:
                log.error(f"Failed to convert entry in section {section_key}: {str(e)}")
                continue

        return resources

    def _render_resource_from_entry(
        self, entry: Dict, section_key: str, template: Type[Template]
    ) -> Optional[Dict]:
        """Renders a FHIR resource dictionary from a CDA entry using templates.

        Args:
            entry: CDA entry dictionary
            section_key: Section identifier (e.g. "problems")
            template: Template to use for rendering

        Returns:
            FHIR resource dictionary or None if rendering fails
        """
        try:
            # Get validated section configuration
            try:
                section_config = self.config.get_cda_section_configs(section_key)
            except ValueError as e:
                log.error(
                    f"Failed to get CDA section config for {section_key}: {str(e)}"
                )
                return None

            # Create context with entry data and config
            context = {"entry": entry, "config": section_config}

            # Render template with context
            return self.render_template(template, context)

        except Exception as e:
            log.error(f"Failed to render resource for section {section_key}: {str(e)}")
            return None

    def _validate_fhir_resource(
        self, resource_dict: Dict, resource_type: str
    ) -> Optional[Resource]:
        """Validates and creates a FHIR resource from a dictionary.
        Adds required fields.

        Args:
            resource_dict: FHIR resource dictionary
            resource_type: FHIR resource type

        Returns:
            FHIR resource or None if validation fails
        """

        try:
            resource_dict = self._add_required_fields(resource_dict, resource_type)
            resource = create_resource_from_dict(resource_dict, resource_type)
            if resource:
                return resource
        except Exception as e:
            log.error(f"Failed to validate FHIR resource: {str(e)}")
            return None

    def _add_required_fields(self, resource_dict: Dict, resource_type: str) -> Dict:
        """Add required fields to FHIR resource dictionary based on resource type.
        Currently only supports Condition, MedicationStatement, and AllergyIntolerance.

        Args:
            resource_dict: Dictionary representation of the resource
            resource_type: Type of FHIR resource

        Returns:
            Dict: Resource dictionary with required fields added
        """
        # Add common fields
        id_prefix = self.config.get_config_value("defaults.common.id_prefix", "hc-")
        if "id" not in resource_dict:
            resource_dict["id"] = f"{id_prefix}{str(uuid.uuid4())}"

        # Get default values from configuration if available
        default_subject = self.config.get_config_value("defaults.common.subject")

        # Add resource-specific required fields
        if resource_type == "Condition":
            if "subject" not in resource_dict:
                resource_dict["subject"] = default_subject

            if "clinicalStatus" not in resource_dict:
                default_status = self.config.get_config_value(
                    "defaults.resources.Condition.clinicalStatus"
                )
                resource_dict["clinicalStatus"] = default_status
        elif resource_type == "MedicationStatement":
            if "subject" not in resource_dict:
                resource_dict["subject"] = default_subject
            if "status" not in resource_dict:
                default_status = self.config.get_config_value(
                    "defaults.resources.MedicationStatement.status"
                )
                resource_dict["status"] = default_status
        elif resource_type == "AllergyIntolerance":
            if "patient" not in resource_dict:
                resource_dict["patient"] = default_subject
            if "clinicalStatus" not in resource_dict:
                default_status = self.config.get_config_value(
                    "defaults.resources.AllergyIntolerance.clinicalStatus"
                )
                resource_dict["clinicalStatus"] = default_status

        return resource_dict

    def generate_resources_from_hl7v2_entries(
        self, entries: List[Dict], message_key: str
    ) -> List[Dict]:
        """
        Convert HL7v2 message entries into FHIR resources.
        This is a placeholder implementation.

        Args:
            entries: List of HL7v2 message entries to convert
            message_key: Key identifying the message type

        Returns:
            List of FHIR resources
        """
        log.warning(
            "FHIR resource generation from HL7v2 is a placeholder implementation"
        )
        return []
