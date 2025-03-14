"""
CDA Generator for HealthChain Interoperability Engine

This module provides functionality for generating CDA documents.
"""

import logging
import json
import re
import xmltodict
import uuid
from datetime import datetime
from typing import Dict, List, Union, Optional

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle

from healthchain.interop.template_renderer import TemplateRenderer

log = logging.getLogger(__name__)


class CDAGenerator(TemplateRenderer):
    """Handles generation of CDA documents"""

    def render_entry(
        self,
        resource: Resource,
        section_key: str,
        template_name: str,
    ) -> Optional[Dict]:
        """Render a single entry for a resource

        Args:
            resource: FHIR resource
            section_key: Key identifying the section
            template_name: Name of the template to use

        Returns:
            Dictionary representation of the rendered entry
        """
        try:
            # Get section configuration
            section_config = self.get_section_config(section_key)

            # Create context with common values
            timestamp_format = self.config_manager.get_config_value(
                "formats.date.timestamp", "%Y%m%d"
            )
            timestamp = datetime.now().strftime(format=timestamp_format)

            # Generate reference name using configured format
            id_format = self.config_manager.get_config_value(
                "formats.ids.reference_name", "#{uuid}name"
            )
            reference_name = id_format.replace("{uuid}", str(uuid.uuid4())[:8])

            # Create context with additional rendering options
            context = {
                "timestamp": timestamp,
                "text_reference_name": reference_name,
                "rendering": self.config_manager.get_config_value(
                    f"sections.{section_key}.rendering", {}
                ),
                "resource": resource.model_dump(),
                "config": section_config,
            }

            # Get template and render
            template = self.get_template(template_name)
            if not template:
                return None

            return self.render_template(template, context)

        except Exception as e:
            log.error(f"Failed to render {section_key} entry: {str(e)}")
            return None

    def render_sections(self, section_entries: Dict) -> List[Dict]:
        """Render all sections with their entries

        Args:
            section_entries: Dictionary mapping section keys to their entries

        Returns:
            List of formatted section dictionaries
        """
        formatted_sections = []

        # Get section configurations
        section_configs = self.get_section_configs()

        # Get section template name from config or use default
        section_template_name = self.config_manager.get_config_value(
            "templates.core.section", "cda_section"
        )

        # Get the section template
        section_template = self.get_template(section_template_name)
        if not section_template:
            raise ValueError(f"Required template '{section_template_name}' not found")

        for section_key, section_config in section_configs.items():
            entries = section_entries.get(section_key, [])
            if entries:
                try:
                    context = {
                        "entries": entries,
                        "config": section_config,
                    }
                    rendered = self.render_template(section_template, context)
                    if rendered:
                        formatted_sections.append(rendered)
                except Exception as e:
                    log.error(f"Failed to render section {section_key}: {str(e)}")

        return formatted_sections

    def generate_document(
        self,
        resources: Union[Resource, List[Resource], Bundle],
        document_config: Dict,
        formatted_sections: List[Dict],
    ) -> str:
        """Generate the final CDA document

        Args:
            resources: FHIR resources
            document_config: Configuration for the document
            formatted_sections: List of formatted section dictionaries

        Returns:
            CDA document as XML string
        """
        # Get document template name from config or use default
        document_template_name = self.config_manager.get_config_value(
            "templates.core.document", "cda_document"
        )

        # Get the document template
        document_template = self.get_template(document_template_name)
        if not document_template:
            raise ValueError(f"Required template '{document_template_name}' not found")

        # Create document context with additional configuration
        context = {
            "bundle": resources if isinstance(resources, Bundle) else None,
            "config": document_config,
            "sections": formatted_sections,
            "defaults": {
                "patient": self.config_manager.get_config_value(
                    "document.defaults.patient", {}
                ),
                "author": self.config_manager.get_config_value(
                    "document.defaults.author", {}
                ),
                "custodian": self.config_manager.get_config_value(
                    "document.defaults.custodian", {}
                ),
            },
            "structure": self.config_manager.get_config_value("document.structure", {}),
            "rendering": self.config_manager.get_config_value("document.rendering", {}),
        }

        # Render document
        rendered = document_template.render(**context)
        document_dict = json.loads(rendered)

        # Get XML formatting options
        pretty_print = self.config_manager.get_config_value(
            "document.rendering.xml.pretty_print", True
        )
        encoding = self.config_manager.get_config_value(
            "document.rendering.xml.encoding", "UTF-8"
        )

        # Generate XML
        xml_string = xmltodict.unparse(
            document_dict, pretty=pretty_print, encoding=encoding
        )

        # Fix self-closing tags
        return re.sub(r"(<(\w+)(\s+[^>]*?)?)></\2>", r"\1/>", xml_string)

    def generate_document_from_resources(
        self,
        resources: Union[Resource, List[Resource], Bundle],
        section_entries_map: Optional[Dict] = None,
    ) -> str:
        """Generate a complete CDA document from FHIR resources

        This method handles the entire process of generating a CDA document:
        1. Creating section entries from resources (if not provided)
        2. Rendering sections
        3. Generating the final document

        Args:
            resources: FHIR resources to include in the document
            section_entries_map: Optional pre-populated section entries map

        Returns:
            CDA document as XML string
        """
        # Get document configuration
        document_config = self.config_manager.get_document_config()
        if not document_config:
            raise ValueError("No document configuration found")

        # If section entries weren't provided, we'll use an empty map
        if section_entries_map is None:
            section_entries_map = {}

        # Render sections
        formatted_sections = self.render_sections(section_entries_map)

        # Generate final CDA document
        return self.generate_document(resources, document_config, formatted_sections)
