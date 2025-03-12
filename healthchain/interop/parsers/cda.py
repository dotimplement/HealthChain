"""
CDA Parser for HealthChain Interoperability Engine

This module provides functionality for parsing CDA XML documents.
"""

import json
import xmltodict
import logging
from typing import Dict, List

from healthchain.interop.filters import clean_empty
from healthchain.interop.models.cda import ClinicalDocument
from healthchain.interop.models.sections import Section, Entry


log = logging.getLogger(__name__)


class CDAParser:
    """Parser for CDA XML documents"""

    def __init__(self, mappings: Dict):
        self.mappings = mappings
        self.clinical_document = None

    def parse_document(self, xml: str, section_configs: Dict) -> Dict[str, List[Dict]]:
        """
        Parse a complete CDA document and extract entries from all configured sections.

        Args:
            xml: The CDA XML document
            section_configs: Configuration for all sections

        Returns:
            Dictionary mapping section keys to lists of entry dictionaries
        """
        section_entries = {}

        # Parse the document once
        try:
            doc_dict = xmltodict.parse(xml)
            self.clinical_document = ClinicalDocument(**doc_dict["ClinicalDocument"])
        except Exception as e:
            log.error(f"Error parsing CDA document: {str(e)}")
            return section_entries

        # Process each section
        for section_key, section_config in section_configs.items():
            try:
                entries = self._parse_section_entries_from_document(section_config)
                if entries:
                    section_entries[section_key] = entries
            except Exception as e:
                log.error(f"Failed to parse section {section_key}: {str(e)}")
                continue

        return section_entries

    def _parse_section_entries_from_document(self, section_config: Dict) -> List[Dict]:
        """
        Extract entries from a CDA section using an already parsed document.

        Args:
            section_config: Configuration for the section containing template ID/code

        Returns:
            List of entry dictionaries from the section
        """
        if not self.clinical_document:
            log.error("No document loaded. Call parse_document or parse_section first.")
            return []

        try:
            # Get all components
            components = self.clinical_document.component.structuredBody.component
            if not isinstance(components, list):
                components = [components]

            # Find matching section
            section = None
            for component in components:
                curr_section = component.section

                if section_config.get(
                    "template_id"
                ) and self._find_section_by_template_id(
                    curr_section, section_config["template_id"]
                ):
                    section = curr_section
                    break

                if section_config.get("code") and self._find_section_by_code(
                    curr_section, section_config["code"]
                ):
                    section = curr_section
                    break

            if not section:
                log.warning(f"Section not found for config: {section_config}")
                return []

            # Get entries and convert to dicts
            entries = self._get_section_entries(section)
            entry_dicts = [
                entry.model_dump(exclude_none=True, by_alias=True)
                for entry in entries
                if entry
            ]

            log.debug(f"Found {len(entry_dicts)} entries in section")

            return entry_dicts

        except Exception as e:
            log.error(f"Error parsing section: {str(e)}")
            return []

    def render_fhir_resource_from_cda_entry(
        self, entry: Dict, template, section_config: Dict
    ) -> Dict:
        """
        Process a CDA entry using a template and prepare it for FHIR conversion

        Args:
            entry: The entry data dictionary
            template: The template to use for rendering
            section_config: Configuration for the section

        Returns:
            Dict: Processed resource dictionary ready for FHIR conversion
        """
        # Render template with entry data and config
        rendered = template.render({"entry": entry, "config": section_config})

        # Parse rendered JSON and clean empty values
        return clean_empty(json.loads(rendered))

    def _find_section_by_template_id(self, section: Section, template_id: str) -> bool:
        """Check if section matches template ID"""
        if not section.templateId:
            return False

        template_ids = (
            section.templateId
            if isinstance(section.templateId, list)
            else [section.templateId]
        )
        return any(tid.root == template_id for tid in template_ids)

    def _find_section_by_code(self, section: Section, code: str) -> bool:
        """Check if section matches code"""
        return section.code and section.code.code == code

    def _get_section_entries(self, section: Section) -> List[Entry]:
        """Get list of entries from section"""
        if not section.entry:
            return []
        return section.entry if isinstance(section.entry, list) else [section.entry]
