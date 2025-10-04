"""
CDA Generator for HealthChain Interoperability Engine

This module provides functionality for generating CDA documents.
"""

import logging
import re
import xmltodict
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fhir.resources.resource import Resource
from healthchain.interop.models.cda import ClinicalDocument
from healthchain.interop.generators.base import BaseGenerator

log = logging.getLogger(__name__)


def _find_section_key_for_resource_type(
    resource_type: str, section_configs: Dict
) -> Optional[str]:
    """Find the appropriate section key for a given resource type

    Args:
        resource_type: FHIR resource type
        section_configs: Dictionary of section configurations

    Returns:
        Section key or None if no matching section found
    """
    # Find matching section for resource type
    section_key = next(
        (
            key
            for key, config in section_configs.items()
            if config.get("resource") == resource_type
        ),
        None,
    )
    return section_key


class CDAGenerator(BaseGenerator):
    """Handles generation of CDA documents from FHIR resources.

    This class provides functionality to convert FHIR resources into CDA (Clinical Document Architecture)
    documents using configurable templates. It handles the mapping of resources to appropriate CDA sections,
    rendering of entries and sections, and generation of the final XML document.

    Example:
        generator = CDAGenerator(config_manager, template_registry)

        # Convert FHIR resources to CDA XML document
        cda_xml = generator.transform(
            resources=fhir_resources,
            document_type="ccd"
        )
    """

    def transform(self, resources: List[Resource], **kwargs: Any) -> str:
        """Transform FHIR resources to CDA format.

        Args:
            resources: List of FHIR resources
            **kwargs:
                document_type: Type of CDA document

        Returns:
            str: CDA document as XML string
        """
        # TODO: add validation
        document_type = kwargs.get("document_type", "ccd")
        return self.generate_document_from_fhir_resources(resources, document_type)

    def generate_document_from_fhir_resources(
        self,
        resources: List[Resource],
        document_type: str,
        validate: bool = True,
    ) -> str:
        """Generate a complete CDA document from FHIR resources

        This method handles the entire process of generating a CDA document:
        1. Mapping FHIR resources to CDA sections (config)
        2. Rendering sections (template)
        3. Generating the final document (template)

        Args:
            resources: FHIR resources to include in the document
            document_type: Type of document to generate
            validate: Whether to validate the CDA document (default: True)

        Returns:
            CDA document as XML string
        """
        mapped_entries = self._get_mapped_entries(resources, document_type)
        sections = self._render_sections(mapped_entries, document_type)

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
            Dictionary representation of the rendered entry (xmltodict)
        """
        try:
            # Get validated section configuration
            section_config = self.config.get_cda_section_configs(config_key)

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
                "resource": resource.model_dump(exclude_none=True),
                "config": section_config,
            }

            # Get template and render
            template = self.get_template_from_section_config(config_key, "entry")
            if template is None:
                log.error(f"Required entry template for '{config_key}' not found")
                return None

            return self.render_template(template, context)

        except Exception as e:
            log.error(f"Failed to render {config_key} entry: {str(e)}")
            return None

    def _get_mapped_entries(
        self, resources: List[Resource], document_type: str = None
    ) -> Dict:
        """Map FHIR resources to CDA section entries by resource type.

        Args:
            resources: List of FHIR resources to map to CDA entries
            document_type: Optional document type to determine which sections to include

        Returns:
            Dictionary mapping section keys (e.g. 'problems', 'medications') to lists of
            their rendered CDA entries. For example:
            {
                'problems': [<rendered condition entry>, ...],
                'medications': [<rendered medication entry>, ...]
            }
        """
        # Get included sections from document config if document_type is provided
        include_sections = None
        if document_type:
            include_sections = self.config.get_config_value(
                f"cda.document.{document_type}.structure.body.include_sections"
            )
            if include_sections:
                log.debug(
                    f"Generating sections: {include_sections} for document type {document_type}"
                )

        section_entries = {}
        for resource in resources:
            # Find matching section for resource type
            resource_type = resource.__class__.__name__
            all_configs = self.config.get_cda_section_configs()
            section_key = _find_section_key_for_resource_type(
                resource_type, all_configs
            )
            if not section_key:
                log.error(f"No section config found for resource type: {resource_type}")
                continue

            # Skip if section is not included in the document config
            if include_sections and section_key not in include_sections:
                log.info(
                    f"Skipping section {section_key} as it's not in include_sections"
                )
                continue

            entry = self._render_entry(resource, section_key)
            if entry:
                section_entries.setdefault(section_key, []).append(entry)

        return section_entries

    def _render_sections(self, mapped_entries: Dict, document_type: str) -> List[Dict]:
        """Render all sections with their entries

        Args:
            mapped_entries: Dictionary mapping section keys to their entries
            document_type: Type of document to generate

        Returns:
            List of formatted section dictionaries

        Raises:
            ValueError: If section configurations or templates are not found
        """
        sections = []

        try:
            # Get validated section configurations
            section_configs = self.config.get_cda_section_configs()
        except ValueError as e:
            log.error(f"Error getting section configs: {str(e)}")
            raise ValueError(f"Failed to load section configurations: {str(e)}")

        # Get section template name from config
        section_template_name = self.config.get_config_value(
            f"cda.document.{document_type}.templates.section"
        )
        if not section_template_name:
            raise ValueError(
                f"No section template found for document type: {document_type}"
            )

        # Get the section template
        section_template = self.get_template(section_template_name)
        if not section_template:
            raise ValueError(f"Required template '{section_template_name}' not found")

        # Render each section that has entries
        for section_key, section_config in section_configs.items():
            entries = mapped_entries.get(section_key, [])
            if entries:
                try:
                    # Special handling for notes section, bit of a hack for now
                    if section_key == "notes":
                        # For DocumentReference, the generated entries already contain the full
                        # section structure, so we need to extract the section directly
                        if (
                            len(entries) > 0
                            and "component" in entries[0]
                            and "section" in entries[0]["component"]
                        ):
                            # Just extract the first section (we don't support multiple notes sections yet)
                            section_data = entries[0]["component"]["section"]
                            sections.append({"section": section_data})
                            continue

                    # Regular handling for other resource types
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

        Raises:
            ValueError: If document configuration or template is not found
        """
        try:
            # Get validated document configuration
            config = self.config.get_cda_document_config(document_type)
        except ValueError as e:
            log.error(f"Error getting document config: {str(e)}")
            raise ValueError(f"Failed to load document configuration: {str(e)}")

        # Get document template name from config
        document_template_name = self.config.get_config_value(
            f"cda.document.{document_type}.templates.document"
        )
        if not document_template_name:
            raise ValueError(
                f"No document template found for document type: {document_type}"
            )

        # Get the document template
        document_template = self.get_template(document_template_name)
        if not document_template:
            raise ValueError(f"Required template '{document_template_name}' not found")

        # Create document context
        # TODO: modify this as bundle metadata is not extracted
        context = {
            "config": config,
            "sections": sections,
        }

        rendered = self.render_template(document_template, context)
        if validate:
            if "ClinicalDocument" not in rendered:
                log.error(
                    "Unable to validate document structure: missing ClinicalDocument"
                )
                out_dict = rendered
            else:
                validated = ClinicalDocument(**rendered["ClinicalDocument"])
                out_dict = {
                    "ClinicalDocument": validated.model_dump(
                        exclude_none=True, exclude_unset=True, by_alias=True
                    )
                }
        else:
            out_dict = rendered

        # Get XML formatting options
        pretty_print = self.config.get_config_value(
            f"cda.document.{document_type}.rendering.xml.pretty_print", True
        )
        encoding = self.config.get_config_value(
            f"cda.document.{document_type}.rendering.xml.encoding", "UTF-8"
        )

        # Generate XML without preprocessor
        xml_string = xmltodict.unparse(out_dict, pretty=pretty_print, encoding=encoding)

        # Replace text elements containing < or > with CDATA sections
        # This regex matches <text>...</text> tags where content has HTML entities
        def replace_with_cdata(match):
            content = match.group(1)
            # Only process if it contains HTML entities
            if "&lt;" in content or "&gt;" in content:
                # Convert HTML entities back to characters
                import html

                decoded = html.unescape(content)
                return f"<text><![CDATA[{decoded}]]></text>"
            return f"<text>{content}</text>"

        xml_string = re.sub(
            r"<text>(.*?)</text>", replace_with_cdata, xml_string, flags=re.DOTALL
        )

        # Fix self-closing tags
        return re.sub(r"(<(\w+)(\s+[^>]*?)?)></\2>", r"\1/>", xml_string)
