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
from typing import Dict, List, Union

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle

from healthchain.interop.filters import clean_empty

log = logging.getLogger(__name__)


class CDAGenerator:
    """Handles generation of CDA documents"""

    def __init__(self, config_manager, template_registry):
        """Initialize the CDA generator

        Args:
            config_manager: Configuration manager instance
            template_registry: Template registry instance
        """
        self.config_manager = config_manager
        self.template_registry = template_registry

    def render_entry(
        self,
        resource: Resource,
        section_key: str,
        template_name: str,
        section_config: Dict,
    ) -> Dict:
        """Render a single entry for a resource

        Args:
            resource: FHIR resource
            section_key: Key identifying the section
            template_name: Name of the template to use
            section_config: Configuration for the section

        Returns:
            Dictionary representation of the rendered entry
        """
        try:
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
                "formats": self.config_manager.get_config_value("formats", {}),
            }

            # Get template and render
            template = self.template_registry.get_template(template_name)
            entry_json = template.render(
                resource=resource.model_dump(),
                config=section_config,
                context=context,
            )

            # Parse and clean the rendered JSON
            return clean_empty(json.loads(entry_json))

        except Exception as e:
            log.error(f"Failed to render {section_key} entry: {str(e)}")
            return None

    def render_sections(
        self, section_entries: Dict, section_configs: Dict
    ) -> List[Dict]:
        """Render all sections with their entries

        Args:
            section_entries: Dictionary mapping section keys to their entries
            section_configs: Configuration for each section

        Returns:
            List of formatted section dictionaries
        """
        formatted_sections = []

        # Get section template name from config or use default
        section_template_name = self.config_manager.get_config_value(
            "templates.core.section", "cda_section"
        )

        try:
            section_template = self.template_registry.get_template(
                section_template_name
            )
        except KeyError:
            raise ValueError(f"Required template '{section_template_name}' not found")

        for section_key, section_config in section_configs.items():
            entries = section_entries.get(section_key, [])
            if entries:
                try:
                    section_json = section_template.render(
                        entries=entries,
                        config=section_config,
                    )
                    formatted_sections.append(json.loads(section_json))
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

        try:
            document_template = self.template_registry.get_template(
                document_template_name
            )
        except KeyError:
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
        document_json = document_template.render(**context)
        document_dict = json.loads(document_json)

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
