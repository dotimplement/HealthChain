import xmltodict
import logging

from typing import Dict, List

from healthchain.interop.models.cda import ClinicalDocument
from healthchain.interop.models.sections import Section, Entry

log = logging.getLogger(__name__)


class CDAParser:
    """Parser for CDA XML documents"""

    def __init__(self, mappings: Dict):
        self.mappings = mappings
        self.clinical_document = None

    def parse_section(self, xml: str, section_config: Dict) -> List[Dict]:
        """
        Extract entries from a CDA section using template ID or code.

        Args:
            xml: The CDA XML document
            section_config: Configuration for the section containing template ID/code

        Returns:
            List of entry dictionaries from the section
        """
        try:
            # Parse XML into ClinicalDocument model
            doc_dict = xmltodict.parse(xml)
            self.clinical_document = ClinicalDocument(**doc_dict["ClinicalDocument"])

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
            log.error(f"Error parsing CDA document: {str(e)}")
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
