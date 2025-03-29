"""
CDA Generator for HealthChain Interoperability Engine

This module provides functionality for generating CDA documents.
"""

import logging
import re
import xmltodict
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fhir.resources.resource import Resource
from healthchain.interop.models.cda import ClinicalDocument
from healthchain.interop.template_renderer import TemplateRenderer
from healthchain.interop.utils import find_section_key_for_resource_type

log = logging.getLogger(__name__)


class CDAGenerator(TemplateRenderer):
    """Handles generation of CDA documents"""

    def generate_document_from_fhir_resources(
        self,
        resources: List[Resource],
        document_type: str,
        validate: bool = True,
    ) -> str:
        """Generate a complete CDA document from FHIR resources

        This method handles the entire process of generating a CDA document:
        1. Creating section entries from resources (if not provided)
        2. Rendering sections
        3. Generating the final document

        Args:
            resources: FHIR resources to include in the document

        Returns:
            CDA document as XML string
        """
        mapped_entries = self._get_mapped_entries(resources)
        sections = self._render_sections(mapped_entries)

        # Generate final CDA document
        return self._render_document(sections, document_type, validate=validate)

    def _render_entry(
        self,
        resource: Resource,
        config_key: str,
    ) -> Optional[Dict]:
        """Render a single entry for a resource

        Args:
            resource: FHIR resource
            config_key: Key identifying the section

        Returns:
            Dictionary representation of the rendered entry
        """
        try:
            # Get validated section configuration
            section_config = self.get_cda_section_config(config_key)

            timestamp_format = self.config.get_config_value(
                "defaults.common.timestamp", "%Y%m%d"
            )
            timestamp = datetime.now().strftime(format=timestamp_format)

            id_format = self.config.get_config_value(
                "defaults.common.reference_name", "#{uuid}name"
            )
            reference_name = id_format.replace("{uuid}", str(uuid.uuid4())[:8])

            # Create context
            context = {
                "timestamp": timestamp,
                "text_reference_name": reference_name,
                "resource": resource.model_dump(),
                "config": section_config,
            }

            # Get template and render
            template_name = self.get_section_template_name(config_key, "entry")
            template = self.get_template(template_name)
            if not template:
                raise ValueError(f"Required template '{template_name}' not found")

            return self.render_template(template, context)

        except Exception as e:
            log.error(f"Failed to render {config_key} entry: {str(e)}")
            return None

    def _get_mapped_entries(self, resources: List[Resource]) -> Dict:
        """Map FHIR resources to CDA section entries

        Args:
            resources: List of FHIR resources

        Returns:
            Dictionary mapping section keys to their entries
        """
        section_entries = {}
        for resource in resources:
            # Find matching section for resource type
            resource_type = resource.__class__.__name__
            all_configs = self.config.get_section_configs()
            section_key = find_section_key_for_resource_type(resource_type, all_configs)

            if not section_key:
                continue

            entry = self._render_entry(resource, section_key)
            if entry:
                section_entries.setdefault(section_key, []).append(entry)

        return section_entries

    def _render_sections(self, mapped_entries: Dict) -> List[Dict]:
        """Render all sections with their entries

        Args:
            section_entries: Dictionary mapping section keys to their entries

        Returns:
            List of formatted section dictionaries
        """
        sections = []

        # Get validated section configurations
        section_configs = self.config.get_section_configs()
        if not section_configs:
            raise ValueError("No valid configurations found in /sections")

        # Get section template name from config or use default
        section_template_name = self.config.get_config_value(
            "document.cda.templates.section", "cda_section"
        )
        # Get the section template
        section_template = self.get_template(section_template_name)
        if not section_template:
            raise ValueError(f"Required template '{section_template_name}' not found")

        for section_key, section_config in section_configs.items():
            entries = mapped_entries.get(section_key, [])
            if entries:
                try:
                    context = {
                        "entries": entries,
                        "config": section_config,
                    }
                    rendered = self.render_template(section_template, context)
                    if rendered:
                        sections.append(rendered)
                except Exception as e:
                    log.error(f"Failed to render section {section_key}: {str(e)}")

        return sections

    def _render_document(
        self,
        sections: List[Dict],
        document_type: str,
        validate: bool = True,
    ) -> str:
        """Generate the final CDA document

        Args:
            sections: List of formatted section dictionaries
            document_type: Type of document to generate
            validate: Whether to validate the CDA document

        Returns:
            CDA document as XML string
        """
        config = self.config.get_document_config(document_type)
        if not config:
            raise ValueError(
                f"No document configuration found for document type: {document_type}"
            )

        # Get document template name from config or use default
        document_template_name = self.config.get_config_value(
            "document.cda.templates.document", "cda_document"
        )
        # Get the document template
        document_template = self.get_template(document_template_name)
        if not document_template:
            raise ValueError(f"Required template '{document_template_name}' not found")

        # Create document context
        context = {
            "config": config,
            "sections": sections,
        }

        rendered = self.render_template(document_template, context)

        if validate:
            validated = ClinicalDocument(**rendered["ClinicalDocument"])

        # Get XML formatting options
        pretty_print = self.config.get_config_value(
            "document.cda.rendering.xml.pretty_print", True
        )
        encoding = self.config.get_config_value(
            "document.cda.rendering.xml.encoding", "UTF-8"
        )
        if validate:
            out_dict = {
                "ClinicalDocument": validated.model_dump(
                    exclude_none=True, exclude_unset=True, by_alias=True
                )
            }
        else:
            out_dict = rendered

        # Generate XML
        xml_string = xmltodict.unparse(
            out_dict,
            pretty=pretty_print,
            encoding=encoding,
        )

        # Fix self-closing tags
        return re.sub(r"(<(\w+)(\s+[^>]*?)?)></\2>", r"\1/>", xml_string)
