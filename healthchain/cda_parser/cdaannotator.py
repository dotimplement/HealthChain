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
from healthchain.models.data.concept import Concept, Quantity, Range, TimeInterval

from .model.cda import ClinicalDocument
from .model.sections import Entry, Section, EntryRelationship, Observation


log = logging.getLogger(__name__)


def get_problem_concept_from_cda_value(value: Dict) -> ProblemConcept:
    """
    Retrieves a ProblemConcept object from a CDA value dictionary.

    Args:
        value (Dict): The CDA value dictionary.

    Returns:
        ProblemConcept: The ProblemConcept object created from the CDA value dictionary.
    """
    concept = ProblemConcept(_standard="cda")
    concept.code = value.get("@code")
    concept.code_system = value.get("@codeSystem")
    concept.code_system_name = value.get("@codeSystemName")
    concept.display_name = value.get("@displayName")

    return concept


def get_time_range_from_cda_value(value: Dict) -> Range:
    """
    Converts a dictionary representing a time range from a CDA value into a Range object.

    Args:
        value (Dict): A dictionary representing the CDA value.

    Returns:
        Range: A Range object representing the time range.

    """
    range_model = Range(
        low=Quantity(
            value=value.get("low", {}).get("@value"),
            unit=value.get("low", {}).get("@unit"),
        ),
        high=Quantity(
            value=value.get("high", {}).get("@value"),
            unit=value.get("high", {}).get("@unit"),
        ),
    )
    if range_model.low.value is None:
        range_model.low = None
    if range_model.high.value is None:
        range_model.high = None

    return range_model


def get_value_from_entry_relationship(entry_relationship):
    """
    Retrieves the values from the given entry_relationship.

    Args:
        entry_relationship: The entry_relationship object to extract values from.

    Returns:
        A list of values extracted from the entry_relationship.

    """
    values = []
    if isinstance(entry_relationship, list):
        for item in entry_relationship:
            if item.observation:
                values.append(item.observation.value)
    else:
        if entry_relationship.observation:
            values.append(entry_relationship.observation.value)
    return values


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
        export(pretty_print: bool = True) -> str: Exports the CDA document as an XML string.
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

    def _extract_problems(self) -> List[ProblemConcept]:
        """
        Extracts problem concepts from the problem section of the CDA document.

        Returns:
            A list of ProblemConcept objects representing the extracted problem concepts.
        """
        if not self._problem_section:
            log.warning("Empty problem section!")
            return []

        concepts = []

        entries = (
            self._problem_section.entry
            if isinstance(self._problem_section.entry, list)
            else [self._problem_section.entry]
        )

        for entry in entries:
            entry_relationship = entry.act.entryRelationship
            values = get_value_from_entry_relationship(entry_relationship)
            for value in values:
                concept = get_problem_concept_from_cda_value(value)
                concepts.append(concept)

        return concepts

    def _extract_medications(self) -> List[MedicationConcept]:
        """
        Extracts medication concepts from the medication section of the CDA document.

        Returns:
            A list of MedicationConcept objects representing the extracted medication concepts.
        """
        if not self._medication_section:
            log.warning("Empty medication section!")
            return []

        def get_medication_from_entry(entry: Entry) -> MedicationConcept:
            substance_administration = entry.substanceAdministration
            if not substance_administration:
                log.warning("Substance administration not found in entry.")
                return None

            # Get the medication code from the consumable
            consumable = substance_administration.consumable
            manufactured_product = (
                consumable.manufacturedProduct if consumable else None
            )
            manufactured_material = (
                manufactured_product.manufacturedMaterial
                if manufactured_product
                else None
            )
            code = manufactured_material.code if manufactured_material else None
            if not code:
                log.warning("Code not found in the consumable's manufactured material.")
                return None

            # Create the medication concept
            concept = MedicationConcept(_standard="cda")
            concept.code = code.code
            concept.code_system = code.codeSystem
            concept.code_system_name = code.codeSystemName
            concept.display_name = code.displayName

            # Get the dosage and route information
            if substance_administration.doseQuantity:
                concept.dosage = Quantity(
                    _source=substance_administration.doseQuantity.model_dump(),
                    value=substance_administration.doseQuantity.value,
                    unit=substance_administration.doseQuantity.unit,
                )
            if substance_administration.routeCode:
                concept.route = Concept(
                    code=substance_administration.routeCode.code,
                    code_system=substance_administration.routeCode.codeSystem,
                    code_system_name=substance_administration.routeCode.codeSystemName,
                    display_name=substance_administration.routeCode.displayName,
                )

            # Get the duration and frequency information
            if substance_administration.effectiveTime:
                effective_times = substance_administration.effectiveTime
                effective_times = (
                    effective_times
                    if isinstance(effective_times, list)
                    else [effective_times]
                )
                # TODO: could refactor this into a pydantic validator
                for effective_time in effective_times:
                    if effective_time.get("@xsi:type") == "IVL_TS":
                        concept.duration = get_time_range_from_cda_value(effective_time)
                        concept.duration._source = effective_time
                    elif effective_time.get("@xsi:type") == "PIVL_TS":
                        period = effective_time.get("period")
                        if period:
                            concept.frequency = TimeInterval(
                                period=Quantity(
                                    value=period.get("@value"), unit=period.get("@unit")
                                ),
                                institution_specified=effective_time.get(
                                    "@institutionSpecified"
                                ),
                            )
                        concept.frequency._source = effective_time

            # TODO: this is read-only for now! can also extract status, translations, supply in entryRelationships
            precondition = substance_administration.precondition
            concept.precondition = (
                precondition.model_dump(exclude_none=True, by_alias=True)
                if precondition
                else None
            )

            return concept

        concepts = []

        if isinstance(self._medication_section.entry, list):
            for entry in self._medication_section.entry:
                concept = get_medication_from_entry(entry)
                concepts.append(concept)
        else:
            concept = get_medication_from_entry(self._medication_section.entry)
            concepts.append(concept)

        return concepts

    def _extract_allergies(self) -> List[AllergyConcept]:
        if not self._allergy_section:
            log.warning("Empty allergy section!")
            return []

        concepts = []

        def get_allergy_concept_from_cda_value(
            value: Dict, allergy_type, reaction, severity
        ) -> AllergyConcept:
            concept = AllergyConcept(_standard="cda")
            concept.code = value.get("@code")
            concept.code_system = value.get("@codeSystem")
            concept.code_system_name = value.get("@codeSystemName")
            concept.display_name = value.get("@displayName")

            concept.allergy_type = allergy_type
            concept.reaction = reaction
            concept.severity = severity

            return concept

        def check_for_entry_observation(entry):
            if isinstance(entry, EntryRelationship):
                if entry.observation:
                    return True
            elif isinstance(entry, Observation):
                if entry.entryRelationship:
                    return check_for_entry_observation(entry.entryRelationship)
            return False

        entries = (
            self._allergy_section.entry
            if isinstance(self._allergy_section.entry, list)
            else [self._allergy_section.entry]
        )

        for entry in entries:
            entry_relationship = entry.act.entryRelationship
            values = get_value_from_entry_relationship(entry_relationship)

            allergy_type = None
            reaction = None
            severity = None

            if check_for_entry_observation(entry):
                allergy_type = entry_relationship.observation.code
                if check_for_entry_observation(entry_relationship.observation):
                    reaction = entry_relationship.observation.entry_relationship.observation.value
                    if check_for_entry_observation(
                        entry_relationship.observation.entry_relationship.observation
                    ):
                        severity = entry_relationship.observation.entry_relationship.observation.entry_relationship.observation.value
            for value in values:
                concept = get_allergy_concept_from_cda_value(
                    value, allergy_type, reaction, severity
                )
                concepts.append(concept)
        return concepts

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

    def add_to_problem_list(
        self, problems: List[ProblemConcept], overwrite: bool = False
    ) -> None:
        """
        Adds a list of problem lists to the problems section.

        Args:
            problems (List[ProblemConcept]): A list of problem concepts to be added.
            overwrite (bool, optional): If True, the existing problem list will be overwritten.
                Defaults to False.

        Returns:
            None
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

    def _add_new_medication_entry(
        self,
        new_medication: MedicationConcept,
        timestamp: str,
        subad_id: str,
        medication_reference_name: str,
    ):
        effective_times = []
        if new_medication.frequency:
            effective_times.append(
                {
                    "@xsi:type": "PIVL_TS",
                    "@institutionSpecified": new_medication.frequency.institution_specified,
                    "@operator": "A",
                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "period": {
                        "@unit": new_medication.frequency.period.unit,
                        "@value": new_medication.frequency.period.value,
                    },
                }
            )
        if new_medication.duration:
            low = {"@nullFlavor": "UNK"}
            high = {"@nullFlavor": "UNK"}
            if new_medication.duration.low:
                low = {"@value": new_medication.duration.low.value}
            if new_medication.duration.high:
                high = {"@value": new_medication.duration.high.value}
            effective_times.append(
                {
                    "@xsi:type": "IVL_TS",
                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "low": low,
                    "high": high,
                }
            )

        if len(effective_times) == 1:
            effective_times = effective_times[0]

        template = {
            "substanceAdministration": {
                "@classCode": "SBADM",
                "@moodCode": "INT",
                "templateId": [
                    {"@root": "2.16.840.1.113883.10.20.1.24"},
                    {"@root": "2.16.840.1.113883.3.88.11.83.8"},
                    {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.7"},
                    {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.7.1"},
                    {"@root": "2.16.840.1.113883.3.88.11.32.8"},
                ],
                "id": {"@root": subad_id},
                "statusCode": {"@code": "completed"},
            }
        }
        # Add dosage, route, duration, frequency
        if effective_times:
            template["substanceAdministration"]["effectiveTime"] = effective_times
        if new_medication.route:
            template["substanceAdministration"]["routeCode"] = {
                "@code": new_medication.route.code,
                "@codeSystem": new_medication.route.code_system,
                "@codeSystemDisplayName": new_medication.route.code_system_name,
                "@displayName": new_medication.route.display_name,
            }
        if new_medication.dosage:
            template["substanceAdministration"]["doseQuantity"] = {
                "@value": new_medication.dosage.value,
                "@unit": new_medication.dosage.unit,
            }

        # Add medication entry
        template["substanceAdministration"]["consumable"] = {
            "@typeCode": "CSM",
            "manufacturedProduct": {
                "@classCode": "MANU",
                "templateId": [
                    {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.7.2"},
                    {"@root": "2.16.840.1.113883.10.20.1.53"},
                    {"@root": "2.16.840.1.113883.3.88.11.32.9"},
                    {"@root": "2.16.840.1.113883.3.88.11.83.8.2"},
                ],
                "manufacturedMaterial": {
                    "code": {
                        "@code": new_medication.code,
                        "@codeSystem": new_medication.code_system,
                        "@codeSystemName": new_medication.code_system_name,
                        "@displayName": new_medication.display_name,
                        "originalText": {
                            "reference": {"@value": medication_reference_name}
                        },
                    }
                },
            },
        }

        # Add an Active status
        template["substanceAdministration"]["entryRelationship"] = (
            {
                "@typeCode": "REFR",
                "observation": {
                    "@classCode": "OBS",
                    "@moodCode": "EVN",
                    "effectiveTime": {"low": {"@value": timestamp}},
                    "templateId": {"@root": "2.16.840.1.113883.10.20.1.47"},
                    "code": {
                        "@code": "33999-4",
                        "@codeSystem": "2.16.840.1.113883.6.1",
                        "@codeSystemName": "LOINC",
                        "@displayName": "Status",
                    },
                    "value": {
                        "@code": "755561003",
                        "@codeSystem": "2.16.840.1.113883.6.96",
                        "@codeSystemName": "SNOMED CT",
                        "@xsi:type": "CE",
                        "@displayName": "Active",
                        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    },
                    "statusCode": {"@code": "completed"},
                },
            },
        )
        template["substanceAdministration"]["precondition"] = (
            new_medication.precondition
        )

        if not isinstance(self._medication_section.entry, list):
            self._medication_section.entry = [self._medication_section.entry]

        new_entry = Entry(**template)
        self._medication_section.entry.append(new_entry)

    def add_to_medication_list(
        self, medications: List[MedicationConcept], overwrite: bool = False
    ) -> None:
        """
        Adds medications to the medication list.

        Args:
            medications (List[MedicationConcept]): A list of MedicationConcept objects representing the medications to be added.
            overwrite (bool, optional): If True, the existing medication list will be overwritten. Defaults to False.

        Returns:
            None
        """
        timestamp = datetime.now().strftime(format="%Y%m%d")
        subad_id = str(uuid.uuid4())
        medication_reference_name = "#m" + str(uuid.uuid4())[:8] + "name"

        if overwrite:
            self._medication_section.entry = []
            self.medication_list = []

        for medication in medications:
            self._add_new_medication_entry(
                new_medication=medication,
                timestamp=timestamp,
                subad_id=subad_id,
                medication_reference_name=medication_reference_name,
            )

        self.medication_list.append(medication)

    def _add_new_allergy_entry(
        self,
        new_allergy: AllergyConcept,
        timestamp: str,
        act_id: str,
        allergy_reference_name: str,
    ) -> None:
        """
        Adds a new allergy entry to the allergy section of the CDA document.

        Args:
            new_allergy (AllergyConcept): The new allergy concept to be added.
            timestamp (str): The timestamp of the entry.
            act_id (str): The ID of the act.
            allergy_reference_name (str): The reference name of the allergy.

        Returns:
            None
        """

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
                "text": {"reference": {"@value": allergy_reference_name}},
                "entryRelationship": {
                    "@typeCode": "SUBJ",
                    "@inversionInd": False,
                    "observation": {
                        "@classCode": "OBS",
                        "@moodCode": "EVN",
                        "templateId": [
                            {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.5"},
                            {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.6"},
                            {"@root": "2.16.840.1.113883.10.20.1.18"},
                            {
                                "@root": "1.3.6.1.4.1.19376.1.5.3.1",
                                "@extension": "allergy",
                            },
                            {"@root": "2.16.840.1.113883.10.20.1.28"},
                        ],
                        "text": {"reference": {"@value": allergy_reference_name}},
                        "value": {
                            "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                            "@code": new_allergy.code,
                            "@codeSystem": new_allergy.code_system,
                            "@codeSystemName": new_allergy.code_system_name,
                            "@displayName": new_allergy.display_name,
                            "originalText": {
                                "reference": {"@value": allergy_reference_name}
                            },
                            "@xsi:type": "CD",
                        },
                        "statusCode": {"@code": "completed"},
                    },
                },
            }
        }

        if new_allergy.allergy_type:
            template["act"]["entryRelationship"]["observation"]["code"] = {
                "@code": new_allergy.allergy_type.code,
                "@codeSystem": "2.16.840.1.113883.6.96",
                "@codeSystemName": "SNOMED CT",
                "@displayName": new_allergy.allergy_type.display_name,
            }
        else:
            raise ValueError("Allergy_type code cannot be missing when adding allergy.")

        if new_allergy.reaction:
            template["act"]["entryRelationship"]["observation"]["entryRelationship"] = {
                "@typeCode": "MFST",
                "observation": {
                    "@classCode": "OBS",
                    "@moodCode": "EVN",
                    "templateId": [
                        {"@root": "2.16.840.1.113883.10.20.1.54"},
                        {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.5"},
                        {
                            "@root": "1.3.6.1.4.1.19376.1.5.3.1.4.5",
                            "@extension": "reaction",
                        },
                        {"@root": "2.16.840.1.113883.10.20.1.28"},
                    ],
                    "code": {"@code": "RXNASSESS"},
                    "value": {
                        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                        "@code": new_allergy.reaction.code,
                        "@codeSystem": new_allergy.reaction.code_system,
                        "@displayName": new_allergy.reaction.display_name,
                        "@xsi:type": "CD",
                    },
                    "entryRelationship": [],
                },
            }

        if new_allergy.severity:
            template["act"]["entryRelationship"]["observation"]["entryRelationship"][
                "observation"
            ]["entryRelationship"] = {
                "@typeCode": "SUBJ",
                "observation": {
                    "@classCode": "OBS",
                    "@moodCode": "EVN",
                    "templateId": [
                        {"@root": "2.16.840.1.113883.10.20.1.55"},
                        {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.1"},
                    ],
                    "code": {
                        "@code": "SEV",
                        "@codeSystem": "2.16.840.1.113883.5.4",
                        "@codeSystemName": "ActCode",
                        "@displayName": "Severity",
                    },
                    "value": {
                        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                        "@code": new_allergy.reaction.code,
                        "@codeSystem": new_allergy.reaction.code_system,
                        "@displayName": new_allergy.reaction.display_name,
                        "@xsi:type": "CD",
                    },
                },
            }

        if not isinstance(self._allergy_section.entry, list):
            self._allergy_section.entry = [self._allergy_section.entry]

        new_entry = Entry(**template)
        self._allergy_section.entry.append(new_entry)

    def add_to_allergy_list(
        self, allergies: List[AllergyConcept], overwrite: bool = False
    ) -> None:
        timestamp = datetime.now().strftime(format="%Y%m%d")
        act_id = str(uuid.uuid4())
        allergy_reference_name = "#a" + str(uuid.uuid4())[:8] + "name"

        if overwrite:
            self._allergy_section.entry = []
            self.allergy_list = []

        for allergy in allergies:
            self._add_new_allergy_entry(
                new_allergy=allergy,
                timestamp=timestamp,
                act_id=act_id,
                allergy_reference_name=allergy_reference_name,
            )

        self.allergy_list.append(allergy)

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
