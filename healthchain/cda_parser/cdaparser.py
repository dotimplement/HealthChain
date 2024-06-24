import xmltodict

from enum import Enum
from collections import deque
from typing import Dict, Optional

from .model.cda import CDA
from .model.sections import Section


class SectionId(Enum):
    PROBLEMS = "2.16.840.1.113883.10.20.1.11"
    MEDICATION = "2.16.840.1.113883.10.20.1.8"
    ALLERGIES = "2.16.840.1.113883.10.20.1.2"
    NOTE = "1.2.840.114350.1.72.1.200001"


def search_key(dictionary: Dict, key: str) -> Optional[str]:
    if key in dictionary:
        return dictionary[key]

    for k, v in dictionary.items():
        if isinstance(v, dict):
            result = search_key(v, key)
            if result is not None:
                return result

    return None


def search_key_breadth_first(dictionary: Dict, key: str) -> Optional[str]:
    queue = deque([dictionary])

    while queue:
        current_dict = queue.popleft()

        if key in current_dict:
            return current_dict[key]

        for k, v in current_dict.items():
            if isinstance(v, dict):
                queue.append(v)

    return None


def insert_at_key(dictionary: Dict, key: str, value: str) -> bool:
    if key in dictionary:
        dictionary[key] = value
        return True

    for k, v in dictionary.items():
        if isinstance(v, dict):
            result = insert_at_key(v, key, value)
            if result:
                return True

    return False


def search_key_from_xml_string(xml: str, key: str):
    xml_dict = xmltodict.parse(xml)

    return search_key(xml_dict, key)


class LazyCdaParser:
    def __init__(self, cda_data: CDA, extractor_method="LLM") -> None:
        self.clinical_document = cda_data
        self.extractor_method = extractor_method
        self._get_ccd_sections()

    @classmethod
    def from_dict(cls, data: Dict):
        clinical_document_model = CDA(**data.get("ClinicalDocument", {}))
        return cls(cda_data=clinical_document_model)

    def _get_ccd_sections(self):
        self.problems_section = self._find_problems_section()
        self.medications_section = self._find_medications_section()
        self.allergies_section = self.allergies_section()
        self.notes_section = self._find_notes_section()

    def _find_section_by_template_id(self, section_id) -> Optional[Section]:
        components = self.clinical_document.component.structuredBody.component

        # Ensure components is a list
        if not isinstance(components, list):
            components = [components]

        for component in components:
            template_ids = component.section.templateId
            if isinstance(template_ids, list):
                for template_id in template_ids:
                    if template_id.root == section_id:
                        return component.section
            elif template_ids.root == section_id:
                return component.section

        return None

    def _find_problems_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(
            self.clinical_document, SectionId.PROBLEMS.value
        )

    def _find_medications_section(self) -> Optional[Section]:
        return self.find_section_by_id(
            self.clinical_document, SectionId.MEDICATIONS.value
        )

    def _find_allergies_section(self) -> Optional[Section]:
        return self.find_section_by_id(
            self.clinical_document, SectionId.ALLERGIES.value
        )

    def _find_notes_section(self) -> Optional[Section]:
        return self.find_section_by_id(self.clinical_document, SectionId.NOTE.value)

    def extract_to_fhir(self):
        pass

    def add_to_problem_list(self, problems):
        pass

    def add_to_allergy_list(self, allergies):
        pass

    def add_to_medication_list(self, medications):
        pass
