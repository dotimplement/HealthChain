import xmltodict
import uuid
import re
import logging

from enum import Enum
from datetime import datetime
from typing import Dict, Optional, List

from healthchain.models import (
    ProblemConcept,
    MedicationConcept,
    AllergyConcept,
)

from .model.cda import ClinicalDocument
from .model.sections import Entry, Section


log = logging.getLogger(__name__)


def get_concept_from_cda_value(value: Dict) -> ProblemConcept:
    # TODO use cda data types
    concept = ProblemConcept()
    concept.code = value.get("@code")
    concept.code_system = value.get("@codeSystem")
    concept.code_system_name = value.get("@codeSystemName")
    concept.display_name = value.get("@displayName")

    return concept


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


class CdaAnnotator:
    """
    Annotates a Clinical Document Architecture (CDA) document.

    Args:
        cda_data (ClinicalDocument): The CDA document data.
        fallback (str, optional): The fallback value. Defaults to "LLM".

    Attributes:
        clinical_document (ClinicalDocument): The CDA document data.
        fallback (str): The fallback value.
        problem_list (List[ProblemConcept]): The list of problems extracted from the CDA document.
        medication_list (List[MedicationConcept]): The list of medications extracted from the CDA document.
        allergy_list (List[AllergyConcept]): The list of allergies extracted from the CDA document.
        note (str): The note extracted from the CDA document.

    Methods:
        from_dict(cls, data: Dict): Creates a CdaAnnotator instance from a dictionary.
        from_xml(cls, data: str): Creates a CdaAnnotator instance from an XML string.
        add_to_problem_list(problems: List[ProblemConcept], overwrite: bool = False) -> None: Adds a list of problem concepts to the problems section.
    """

    def __init__(self, cda_data: ClinicalDocument, fallback="LLM") -> None:
        self.clinical_document = cda_data
        self.fallback = fallback
        self._get_ccd_sections()
        self._extract_data()

    @classmethod
    def from_dict(cls, data: Dict):
        """
        Creates an instance of the class from a dictionary.

        Args:
            data (Dict): The dictionary containing the dictionary representation of the cda xml (using xmltodict.parse).

        Returns:
            CdaAnnotator: An instance of the class initialized with the data from the dictionary.
        """
        clinical_document_model = ClinicalDocument(**data.get("ClinicalDocument", {}))
        return cls(cda_data=clinical_document_model)

    @classmethod
    def from_xml(cls, data: str):
        """
        Creates an instance of the CDAAnnotator class from an XML string.

        Args:
            data (str): The XML string representing the CDA document.

        Returns:
            CDAAnnotator: An instance of the CDAAnnotator class initialized with the parsed CDA data.
        """
        cda_dict = xmltodict.parse(data)
        clinical_document_model = ClinicalDocument(
            **cda_dict.get("ClinicalDocument", {})
        )
        return cls(cda_data=clinical_document_model)

    def __str__(self):
        problems = ""
        allergies = ""
        medications = ""

        if self.problem_list:
            problems = "\n".join(
                [problem.model_dump_json() for problem in self.problem_list]
            )
        if self.allergy_list:
            allergies = "\n".join(
                [allergy.model_dump_json() for allergy in self.allergy_list]
            )
        if self.medication_list:
            medications = "\n".join(
                [medication.model_dump_json() for medication in self.medication_list]
            )

        return problems + allergies + medications

    def _get_ccd_sections(self) -> None:
        """
        Retrieves the different sections of the CCD document.

        This method finds and assigns the problem section, medication section,
        allergy section, and note section of the CCD document.

        Returns:
            None
        """
        self._problem_section = self._find_problems_section()
        self._medication_section = self._find_medications_section()
        self._allergy_section = self._find_allergies_section()
        self._note_section = self._find_notes_section()

    def _extract_data(self) -> None:
        """
        Extracts data from the CDA document and assigns it to instance variables.

        This method extracts problem list, medication list, allergy list, and note from the CDA document
        and assigns them to the corresponding instance variables.

        Returns:
            None
        """
        self.problem_list: List[ProblemConcept] = self._extract_problems()
        self.medication_list: List[MedicationConcept] = self._extract_medications()
        self.allergy_list: List[AllergyConcept] = self._extract_allergies()
        self.note: str = self._extract_note()

    def _find_section_by_template_id(self, section_id: str) -> Optional[Section]:
        """
        Finds a section in the clinical document by its template ID.

        Args:
            section_id (str): The template ID of the section to find.

        Returns:
            Optional[Section]: The section with the specified template ID, or None if not found.
        """
        # NOTE not all CDAs have template ids in each section (don't ask me why)
        # TODO: It's probably safer to parse by 'code' which is a required field
        components = self.clinical_document.component.structuredBody.component
        # Ensure components is a list
        if not isinstance(components, list):
            components = [components]

        for component in components:
            template_ids = component.section.templateId
            if template_ids is None:
                continue

            if isinstance(template_ids, list):
                for template_id in template_ids:
                    if template_id.root == section_id:
                        return component.section
            elif template_ids.root == section_id:
                return component.section

        log.warning(f"Unable to find section templateId {section_id}")

        return None

    def _find_problems_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(SectionId.PROBLEM.value)

    def _find_medications_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(SectionId.MEDICATION.value)

    def _find_allergies_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(SectionId.ALLERGY.value)

    def _find_notes_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(SectionId.NOTE.value)

    def _add_new_problem_entry(
        self,
        new_problem: ProblemConcept,
        timestamp: str,
        act_id: str,
        problem_reference_name: str,
    ) -> None:
        """
        Adds a new problem entry to the problem section of the CDA document.

        Args:
            new_problem (ProblemConcept): The new problem concept to be added.
            timestamp (str): The timestamp of the entry.
            act_id (str): The ID of the act.
            problem_reference_name (str): The reference name of the problem.

        Returns:
            None
        """
        # TODO: This will need work
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
                "code": {"@nullflavor": "NA"},
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
        if not isinstance(self._problem_section.entry, list):
            self._problem_section.entry = [self._problem_section.entry]

        new_entry = Entry(**template)
        self._problem_section.entry.append(new_entry)

    def _extract_problems(self) -> List[ProblemConcept]:
        """
        Extracts problem concepts from the problem section of the CDA document.

        Returns:
            A list of ProblemConcept objects representing the extracted problem concepts.
        """
        # idea - llm extraction
        if not self._problem_section:
            log.warning("Empty problem section!")
            return []

        concepts = []
        if isinstance(self._problem_section.entry, list):
            for entry in self._problem_section.entry:
                entry_relationship = entry.act.entryRelationship
                if isinstance(entry_relationship, list):
                    for entry_relationship_item in entry_relationship:
                        if entry_relationship_item.observation:
                            value = entry_relationship_item.observation.value
                else:
                    value = entry.act.entryRelationship.observation.value
                concept = get_concept_from_cda_value(value)
                concepts.append(concept)
        else:
            value = self._problem_section.entry.act.entryRelationship.observation.value
            concept = get_concept_from_cda_value(value)
            concepts.append(concept)

        return concepts

    def _extract_medications(self) -> List[MedicationConcept]:
        pass

    def _extract_allergies(self) -> List[AllergyConcept]:
        pass

    def _extract_note(self) -> str:
        """
        Extracts the note section from the CDA document.

        Returns:
            str: The extracted note section as a string.
        """
        # TODO: need to handle / escape html tags within the note section, parse with right field
        if not self._note_section:
            log.warning("Empty notes section!")
            return []

        return self._note_section.text

    def add_to_problem_list(
        self, problems: List[ProblemConcept], overwrite: bool = False
    ) -> None:
        """
        Adds a list of problem lists to the problems section
        """
        timestamp = datetime.now().strftime(format="%Y%m%d")
        act_id = str(uuid.uuid4())
        problem_reference_name = "#p" + str(uuid.uuid4())[:8] + "name"

        if overwrite:
            self._problem_section.entry = []
            self.problem_list = []

        for problem in problems:
            self._add_new_problem_entry(
                new_problem=problem,
                timestamp=timestamp,
                act_id=act_id,
                problem_reference_name=problem_reference_name,
            )

        self.problem_list.append(problem)

    def add_to_allergy_list(
        self, allergies: List[AllergyConcept], overwrite: bool = False
    ) -> None:
        raise NotImplementedError("Allergy list not implemented yet")

    def add_to_medication_list(
        self, medications: List[MedicationConcept], overwrite: bool = False
    ) -> None:
        raise NotImplementedError("Medication list not implemented yet")

    def export(self, pretty_print: bool = True) -> str:
        """
        Exports CDA document as an XML string
        """
        out_string = xmltodict.unparse(
            {
                "ClinicalDocument": self.clinical_document.model_dump(
                    exclude_none=True, exclude_unset=True, by_alias=True
                )
            },
            pretty=pretty_print,
        )
        # Fixes self closing tags - this is not strictly necessary, just looks more readable
        pattern = r"(<(\w+)(\s+[^>]*?)?)></\2>"
        export_xml = re.sub(pattern, r"\1/>", out_string)

        return export_xml
