"""
FHIR Generator for HealthChain Interoperability Engine

This module provides functionality for generating FHIR resources from templates.
"""

import logging
from typing import Dict, List, Optional

from healthchain.interop.template_renderer import TemplateRenderer

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

    def convert_entries_to_resources(
        self, entries: List[Dict], section_key: str, resource_type: str
    ) -> List[Dict]:
        """
        Convert entries from a section to FHIR resource dictionaries

        Args:
            entries: List of entries from a section
            section_key: Key identifying the section
            resource_type: Type of FHIR resource to create

        Returns:
            List of FHIR resource dictionaries
        """
        resource_dicts = []
        template = self.get_section_template(section_key, "resource")

        if not template:
            log.error(f"No resource template found for section {section_key}")
            return resource_dicts

        for entry in entries:
            try:
                # Convert entry to FHIR resource dictionary
                resource_dict = self.render_resource_from_entry(
                    entry, section_key, template
                )

                if resource_dict:
                    resource_dicts.append(resource_dict)

            except Exception as e:
                log.error(f"Failed to convert entry in section {section_key}: {str(e)}")
                continue

        return resource_dicts
