import xmltodict
import uuid

from enum import Enum
from datetime import datetime
from collections import deque
from typing import Dict, Optional, List

from healthchain.models.data.concept import (
    Concept,
    ProblemConcept,
    MedicationConcept,
    AllergyConcept,
)

from .model.cda import CDA
from .model.sections import Entry, Section


class SectionId(Enum):
    PROBLEM = "2.16.840.1.113883.10.20.1.11"
    MEDICATION = "2.16.840.1.113883.10.20.1.8"
    ALLERGY = "2.16.840.1.113883.10.20.1.2"
    NOTE = "1.2.840.114350.1.72.1.200001"


class ProblemCodes(Enum):
    CONDITION = "64572001"
    SYMPTOM = "418799008"
    FINDING = "404684003"
    COMPLAINT = "409586006"
    FUNCTIONAL_LIMITATION = "248536006"
    PROBLEM = "55607006"
    DIAGNOSIS = "282291009"


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
        self.allergies_section = self._find_allergies_section()
        self.notes_section = self._find_notes_section()

    def _find_section_by_template_id(self, section_id: str) -> Optional[Section]:
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
        return self._find_section_by_template_id(SectionId.PROBLEM.value)

    def _find_medications_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(SectionId.MEDICATION.value)

    def _find_allergies_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(SectionId.ALLERGY.value)

    def _find_notes_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(SectionId.NOTE.value)

    def _get_concept_from_cda_value(self, value: Dict) -> ProblemConcept:
        concept = ProblemConcept()
        concept.code = value.get("@code")
        concept.code_system = value.get("@codeSystem")
        concept.code_system_name = value.get("@codeSystemName")
        concept.display_name = value.get("@displayName")

        return concept

    def _add_new_problem_entry(
        self,
        new_problem: ProblemConcept,
        timestamp: str,
        act_id: str,
        problem_reference_name: str,
    ) -> None:
        # TODO: this will need work
        template = {
            "act": {
                "@classCode": "ACT",
                "@moodCode": "EVN",
                "templateId": [
                    {"@root": "2.16.840.1.113883.10.20.1.27"},
                    {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.5.1"},
                    {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.5.2"},
                    {"@root": "2.16.840.1.113883.3.88.11.32.7"},
                    {"@root": "2.16.840.1.113883.3.88.11.83.7"},
                ],
                "id": {"@root": act_id},
                "statusCode": {"@code": "active"},
                "effectiveTime": {"low": {"@value": timestamp}},
                "entryRelationship": {
                    "@typeCode": "SUBJ",
                    "@inversionInd": False,
                    "observation": {
                        "@classCode": "OBS",
                        "@moodCode": "EVN",
                        "templateId": [
                            {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.5"},
                            {"@root": "2.16.840.1.113883.10.20.1.28"},
                        ],
                        "id": {"@root": act_id},
                        "code": {
                            "@code": "55607006",
                            "@codeSystem": "2.16.840.1.113883.6.96",
                            "@codeSystemName": "SNOMED CT",
                            "@displayName": "Problem",
                        },
                        "text": {"reference": {"@value": problem_reference_name}},
                        "value": {
                            "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                            "@code": new_problem.code,
                            "@codeSystem": new_problem.code_system,
                            "@codeSystemName": new_problem.code_system_name,
                            "@displayName": new_problem.display_name,
                            "originalText": {
                                "reference": {"@value": problem_reference_name}
                            },
                            "@xsi:type": "CD",
                        },
                        "statusCode": {"@code": "completed"},
                        "effectiveTime": {"low": {"@value": timestamp}},
                        "entryRelationship": {
                            "@typeCode": "REFR",
                            "observation": {
                                "@classCode": "OBS",
                                "@moodCode": "EVN",
                                "code": {
                                    "@code": "33999-4",
                                    "@codeSystem": "2.16.840.1.113883.6.1",
                                    "@displayName": "Status",
                                },
                                "value": {
                                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                                    "@code": "55561003",
                                    "@codeSystem": "2.16.840.1.113883.6.96",
                                    "@displayName": "Active",
                                    "@xsi:type": "CE",
                                },
                                "statusCode": {"@code": "completed"},
                                "effectiveTime": {"low": {"@value": timestamp}},
                            },
                        },
                    },
                },
            }
        }
        if not isinstance(self.problems_section.entry, list):
            self.problems_section.entry = [self.problems_section.entry]

        new_entry = Entry(**template)
        self.problems_section.entry.append(new_entry)

    def extract(self) -> List[Concept]:
        concepts = []
        if isinstance(self.problems_section.entry, list):
            for entry in self.problems_section.entry:
                entry_relationship = entry.act.entryRelationship
                if isinstance(entry_relationship, list):
                    for entry_relationship_item in entry_relationship:
                        if entry_relationship_item.observation:
                            value = entry_relationship_item.observation.value
                else:
                    value = entry.act.entryRelationship.observation.value
                concept = self._get_concept_from_cda_value(value)
                concepts.append(concept)
        else:
            value = self.problems_section.entry.act.entryRelationship.observation.value
            concept = self._get_concept_from_cda_value(value)
            concepts.append(concept)

        return concepts

    def add_to_problem_list(self, problems: List[ProblemConcept]) -> None:
        timestamp = datetime.now().strftime(format="%Y%m%d")
        act_id = str(uuid.uuid4())
        problem_reference_name = "#p" + str(uuid.uuid4())[:8] + "name"

        for problem in problems:
            self._add_new_problem_entry(
                new_problem=problem,
                timestamp=timestamp,
                act_id=act_id,
                problem_reference_name=problem_reference_name,
            )

    def add_to_allergy_list(self, allergies: List[AllergyConcept]) -> None:
        raise NotImplementedError("Method not implemented yet!")

    def add_to_medication_list(self, medications: List[MedicationConcept]) -> None:
        raise NotImplementedError("Method not implemented yet!")
