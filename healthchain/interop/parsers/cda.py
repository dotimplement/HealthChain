"""
CDA Parser for HealthChain Interoperability Engine

This module provides functionality for parsing CDA XML documents.
"""

import xmltodict
import logging
from typing import Dict, List

from healthchain.interop.models.cda import ClinicalDocument
from healthchain.interop.models.sections import Section, Entry
from healthchain.config_manager import ConfigManager

log = logging.getLogger(__name__)


class CDAParser:
    """Parser for CDA XML documents"""

    def __init__(self, config_manager: ConfigManager):
        """Initialize the CDA parser

        Args:
            config_manager: ConfigManager instance for accessing configuration
        """
        self.config_manager = config_manager
        self.clinical_document = None

    def parse_document_sections(self, xml: str) -> Dict[str, List[Dict]]:
        """
        Parse a complete CDA document and extract entries from all configured sections.

        Args:
            xml: The CDA XML document

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

        # Get section configurations
        sections = self.config_manager.get_section_configs()
        if not sections:
            log.warning("No sections found in configuration")
            return section_entries

        # Process each section from the configuration
        for section_key in sections.keys():
            try:
                entries = self._parse_section_entries_from_document(section_key)
                if entries:
                    section_entries[section_key] = entries
            except Exception as e:
                log.error(f"Failed to parse section {section_key}: {str(e)}")
                continue

        return section_entries

    def _parse_section_entries_from_document(self, section_key: str) -> List[Dict]:
        """
        Extract entries from a CDA section using an already parsed document.

        Args:
            section_key: Key identifying the section in the configuration

        Returns:
            List of entry dictionaries from the section
        """
        if not self.clinical_document:
            log.error("No document loaded. Call parse_document first.")
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

                # Get template_id and code from config_manager
                template_id = self.config_manager.get_config_value(
                    f"sections.{section_key}.template_id", None
                )
                code = self.config_manager.get_config_value(
                    f"sections.{section_key}.code", None
                )

                if template_id and self._find_section_by_template_id(
                    curr_section, template_id
                ):
                    section = curr_section
                    break

                if code and self._find_section_by_code(curr_section, code):
                    section = curr_section
                    break

            if not section:
                log.warning(f"Section not found for key: {section_key}")
                return []

            # Get entries and convert to dicts
            entries = self._get_section_entries(section)
            entry_dicts = [
                entry.model_dump(exclude_none=True, by_alias=True)
                for entry in entries
                if entry
            ]

            log.debug(f"Found {len(entry_dicts)} entries in section {section_key}")

            return entry_dicts

        except Exception as e:
            log.error(f"Error parsing section {section_key}: {str(e)}")
            return []

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
