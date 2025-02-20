import xmltodict
import uuid
import re
import logging

from enum import Enum
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Union

from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance

from healthchain.cda_parser.model.datatypes import CD, CE, IVL_PQ
from healthchain.cda_parser.model.cda import ClinicalDocument
from healthchain.cda_parser.model.sections import (
    Entry,
    Section,
    EntryRelationship,
    Observation,
)
from fhir.resources.dosage import Dosage
from healthchain.cda_parser.utils import CodeMapping
from healthchain.fhir import (
    create_condition,
    create_allergy_intolerance,
    create_medication_statement,
    create_single_codeable_concept,
    set_problem_list_item_category,
    create_single_reaction,
)

log = logging.getLogger(__name__)


# def get_time_range_from_cda_value(value: Dict) -> Range:
#     """
#     Converts a dictionary representing a time range from a CDA value into a Range object.

#     Args:
#         value (Dict): A dictionary representing the CDA value.

#     Returns:
#         Range: A Range object representing the time range.

#     """
#     range_model = Range(
#         low=Quantity(
#             value=value.get("low", {}).get("@value"),
#             unit=value.get("low", {}).get("@unit"),
#         ),
#         high=Quantity(
#             value=value.get("high", {}).get("@value"),
#             unit=value.get("high", {}).get("@unit"),
#         ),
#     )
#     if range_model.low.value is None:
#         range_model.low = None
#     if range_model.high.value is None:
#         range_model.high = None

#     return range_model


def get_value_from_entry_relationship(entry_relationship: EntryRelationship) -> List:
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


def check_has_template_id(section: Section, template_id: str) -> bool:
    """
    Check if the given section has a matching template ID.

    Args:
        section: The section to check.
        template_id: The template ID to match.

    Returns:
        True if the section has a matching template ID, False otherwise.
    """

    if section.templateId is None:
        return False

    if isinstance(section.templateId, list):
        for template in section.templateId:
            if template.root == template_id:
                return True
    elif section.templateId.root == template_id:
        return True

    return False


def check_for_entry_observation(entry: Entry) -> bool:
    """
    Checks if the given entry contains an observation.

    Args:
        entry: The entry to check.

    Returns:
        True if the entry contains an observation, False otherwise.
    """
    if isinstance(entry, EntryRelationship):
        if entry.observation:
            return True
    elif isinstance(entry, Observation):
        if entry.entryRelationship:
            return check_for_entry_observation(entry.entryRelationship)
    elif isinstance(entry, list):
        for item in entry:
            if isinstance(item, EntryRelationship):
                if item.observation:
                    return True
            elif isinstance(item, Observation):
                if item.entryRelationship:
                    return check_for_entry_observation(item.entryRelationship)
    return False


class SectionId(Enum):
    PROBLEM = "2.16.840.1.113883.10.20.1.11"
    MEDICATION = "2.16.840.1.113883.10.20.1.8"
    ALLERGY = "2.16.840.1.113883.10.20.1.2"
    NOTE = "1.2.840.114350.1.72.1.200001"


class SectionCode(Enum):
    PROBLEM = "11450-4"
    MEDICATION = "10160-0"
    ALLERGY = "48765-2"
    NOTE = "51847-2"


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
    Limited to problems, medications, allergies, and notes sections for now.

    Args:
        cda_data (ClinicalDocument): The CDA document data.
        fallback (str, optional): The fallback value. Defaults to "LLM".

    Attributes:
        clinical_document (ClinicalDocument): The CDA document data.
        fallback (str): The fallback value.
        problem_list (List[Condition]): The list of problems extracted from the CDA document.
        medication_list (List[MedicationStatement]): The list of medications extracted from the CDA document.
        allergy_list (List[AllergyIntolerance]): The list of allergies extracted from the CDA document.
        note (str): The note extracted from the CDA document.

    Methods:
        from_dict(cls, data: Dict): Creates a CdaAnnotator instance from a dictionary.
        from_xml(cls, data: str): Creates a CdaAnnotator instance from an XML string.
        add_to_problem_list(problems: List[Condition], overwrite: bool = False) -> None: Adds a list of Condition resources to the problems section.
        export(pretty_print: bool = True) -> str: Exports the CDA document as an XML string.
    """

    def __init__(self, cda_data: ClinicalDocument) -> None:
        self.clinical_document = cda_data
        self.code_mapping = CodeMapping()
        self._get_ccd_sections()
        self._extract_data()

    @classmethod
    def from_dict(cls, data: Dict) -> "CdaAnnotator":
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
    def from_xml(cls, data: str) -> "CdaAnnotator":
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
        self.problem_list: List[Condition] = self._extract_problems()
        self.medication_list: List[MedicationStatement] = self._extract_medications()
        self.allergy_list: List[AllergyIntolerance] = self._extract_allergies()
        self.note: str = self._extract_note()

    def _find_section_by_code(self, section_code: str) -> Optional[Section]:
        """
        Finds a section in the clinical document by its code value.

        Args:
            section_code (str): The code of the section to find.

        Returns:
            Optional[Section]: The section with the specified code, or None if not found.
        """
        components = self.clinical_document.component.structuredBody.component

        if not isinstance(components, list):
            components = [components]

        for component in components:
            code = component.section.code.code

            if code is None:
                continue
            if code == section_code:
                return component.section
        log.warning(f"unable to find section with code {section_code}")
        return None

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
        return self._find_section_by_template_id(
            SectionId.PROBLEM.value
        ) or self._find_section_by_code(SectionCode.PROBLEM.value)

    def _find_medications_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(
            SectionId.MEDICATION.value
        ) or self._find_section_by_code(SectionCode.MEDICATION.value)

    def _find_allergies_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(
            SectionId.ALLERGY.value
        ) or self._find_section_by_code(SectionCode.ALLERGY.value)

    def _find_notes_section(self) -> Optional[Section]:
        return self._find_section_by_template_id(
            SectionId.NOTE.value
        ) or self._find_section_by_code(SectionCode.NOTE.value)

    def _extract_problems(self) -> List[Condition]:
        """
        Extracts problems from the CDA document's problem section and converts them to FHIR Condition resources.

        The method processes each problem entry in the CDA document and:
        - Maps CDA status codes to FHIR clinical status
        - Extracts onset and abatement dates
        - Creates FHIR Condition resources with appropriate coding
        - Sets problem list item category
        - Handles both single entries and lists of entries

        Returns:
            List[Condition]: A list of FHIR Condition resources representing the extracted problems.
                           Returns empty list if problem section is not found.
        """
        if not self._problem_section:
            log.warning("Empty problem section!")
            return []

        conditions = []

        def create_fhir_condition_from_cda(value: Dict, entry) -> Condition:
            # Map CDA status to FHIR clinical status
            status = "unknown"
            if hasattr(entry, "act") and hasattr(entry.act, "statusCode"):
                status_code = entry.act.statusCode.code
                status = self.code_mapping.cda_to_fhir(
                    status_code, "status", case_sensitive=False, default="unknown"
                )

            # Extract dates from entry
            onset_date = None
            abatement_date = None
            if hasattr(entry, "act") and hasattr(entry.act, "effectiveTime"):
                effective_time = entry.act.effectiveTime
                if hasattr(effective_time, "low") and effective_time.low:
                    onset_date = CodeMapping.convert_date_cda_to_fhir(
                        effective_time.low.value
                    )

                if hasattr(effective_time, "high") and effective_time.high:
                    abatement_date = CodeMapping.convert_date_cda_to_fhir(
                        effective_time.high.value
                    )

            # Create condition using helper function
            condition = create_condition(
                subject="Patient/123",  # TODO: add patient reference {self.clinical_document.recordTarget.patientRole.id}
                status=status,
                code=value.get("@code"),
                display=value.get("@displayName"),
                system=self.code_mapping.cda_to_fhir(
                    value.get("@codeSystem"), "system"
                ),
            )

            # Add dates if present
            if onset_date:
                condition.onsetDateTime = onset_date
            if abatement_date:
                condition.abatementDateTime = abatement_date

            # Set category (problem-list-item by default for problems section)
            set_problem_list_item_category(condition)

            return condition

        entries = (
            self._problem_section.entry
            if isinstance(self._problem_section.entry, list)
            else [self._problem_section.entry]
        )

        for entry in entries:
            entry_relationship = entry.act.entryRelationship
            values = get_value_from_entry_relationship(entry_relationship)
            for value in values:
                condition = create_fhir_condition_from_cda(value, entry)
                conditions.append(condition)

        return conditions

    def _extract_medications(self) -> List[MedicationStatement]:
        """
        Extracts medication concepts from the medication section of the CDA document.

        Returns:
            A list of MedicationStatement resources representing the extracted medication concepts.
        """
        if not self._medication_section:
            log.warning("Empty medication section!")
            return []

        medications = []

        def create_medication_statement_from_cda(
            code: CD,
            dose_quantity: Optional[IVL_PQ],
            route_code: Optional[CE],
            effective_times: Optional[Union[List[Dict], Dict]],
        ) -> MedicationStatement:
            # Map CDA system to FHIR system
            fhir_system = self.code_mapping.cda_to_fhir(
                code.codeSystem, "system", default="http://snomed.info/sct"
            )

            # Create base medication statement using helper
            medication = create_medication_statement(
                subject="Patient/123",  # TODO: extract patient reference
                status="recorded",  # TODO: extract status
                code=code.code,
                display=code.displayName,
                system=fhir_system,
            )

            # Add dosage if present
            if dose_quantity:
                medication.dosage = [
                    {
                        "doseAndRate": [
                            {
                                "doseQuantity": {
                                    "value": dose_quantity.value,
                                    "unit": dose_quantity.unit,
                                }
                            }
                        ]
                    }
                ]

            # Add route if present
            if route_code:
                route_system = self.code_mapping.cda_to_fhir(
                    route_code.codeSystem, "system", default="http://snomed.info/sct"
                )
                medication.dosage = medication.dosage or [Dosage()]
                medication.dosage[0].route = create_single_codeable_concept(
                    code=route_code.code,
                    display=route_code.displayName,
                    system=route_system,
                )

            # Add timing if present
            if effective_times:
                effective_times = (
                    effective_times
                    if isinstance(effective_times, list)
                    else [effective_times]
                )
                # TODO: could refactor this into a pydantic validator
                for effective_time in effective_times:
                    if effective_time.get("@xsi:type") == "IVL_TS":
                        # Handle duration
                        low_value = effective_time.get("low", {}).get("@value")
                        high_value = effective_time.get("high", {}).get("@value")

                        if low_value or high_value:
                            medication.effectivePeriod = {}
                            if low_value:
                                medication.effectivePeriod.start = (
                                    CodeMapping.convert_date_cda_to_fhir(low_value)
                                )
                            if high_value:
                                medication.effectivePeriod.end = (
                                    CodeMapping.convert_date_cda_to_fhir(high_value)
                                )

                    elif effective_time.get("@xsi:type") == "PIVL_TS":
                        # Handle frequency
                        period = effective_time.get("period")
                        if period:
                            medication.dosage = medication.dosage or [Dosage()]
                            medication.dosage[0].timing = {
                                "repeat": {
                                    "period": float(period.get("@value")),
                                    "periodUnit": period.get("@unit"),
                                }
                            }

            return medication

        entries = (
            self._medication_section.entry
            if isinstance(self._medication_section.entry, list)
            else [self._medication_section.entry]
        )

        for entry in entries:
            substance_administration = entry.substanceAdministration
            if not substance_administration:
                log.warning("Substance administration not found in entry.")
                continue

            # Get medication details
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
                log.warning("Code not found in the consumable")
                continue

            # Create FHIR medication statement
            medication = create_medication_statement_from_cda(
                code=code,
                dose_quantity=substance_administration.doseQuantity,
                route_code=substance_administration.routeCode,
                effective_times=substance_administration.effectiveTime,
            )
            medications.append(medication)

        return medications

    def _extract_allergies(self) -> List[AllergyIntolerance]:
        """
        Extracts allergy concepts from the allergy section of the CDA document.

        Returns:
            List[AllergyIntolerance]: A list of FHIR AllergyIntolerance resources.
        """
        if not self._allergy_section:
            log.warning("Empty allergy section!")
            return []

        allergies = []

        def get_allergy_details_from_entry_relationship(
            entry_relationship: EntryRelationship,
        ) -> Tuple[str, CD, Dict, Dict]:
            allergen_name = None
            allergy_type = None
            reaction = None
            severity = None

            # TODO: Improve this

            entry_relationships = (
                entry_relationship
                if isinstance(entry_relationship, list)
                else [entry_relationship]
            )
            for entry_relationship in entry_relationships:
                if check_for_entry_observation(entry_relationship):
                    allergy_type = entry_relationship.observation.code
                    observation = entry_relationship.observation
                    allergen_name = (
                        observation.participant.participantRole.playingEntity.name
                    )

                    if check_for_entry_observation(observation):
                        observation_entry_relationships = (
                            observation.entryRelationship
                            if isinstance(observation.entryRelationship, list)
                            else [observation.entryRelationship]
                        )
                        for observation_entry_rel in observation_entry_relationships:
                            if check_has_template_id(
                                observation_entry_rel.observation,
                                "1.3.6.1.4.1.19376.1.5.3.1.4.5",
                            ):
                                reaction = observation_entry_rel.observation.value

                        if check_for_entry_observation(
                            observation_entry_rel.observation
                        ):
                            if check_has_template_id(
                                observation_entry_rel.observation.entryRelationship.observation,
                                "1.3.6.1.4.1.19376.1.5.3.1.4.1",
                            ):
                                severity = observation_entry_rel.observation.entryRelationship.observation.value

            return allergen_name, allergy_type, reaction, severity

        entries = (
            self._allergy_section.entry
            if isinstance(self._allergy_section.entry, list)
            else [self._allergy_section.entry]
        )

        for entry in entries:
            entry_relationship = entry.act.entryRelationship
            values = get_value_from_entry_relationship(entry_relationship)

            allergen_name, allergy_type, reaction, severity = (
                get_allergy_details_from_entry_relationship(entry_relationship)
            )

            for value in values:
                # Map CDA system to FHIR system
                allergy_code_system = self.code_mapping.cda_to_fhir(
                    value.get("@codeSystem"), "system", default="http://snomed.info/sct"
                )
                allergy = create_allergy_intolerance(
                    patient="Patient/123",  # TODO: Get from patient context
                    code=value.get("@code"),
                    display=value.get("@displayName"),
                    system=allergy_code_system,
                )
                if allergy.code.coding[0].display is None:
                    allergy.code.coding[0].display = allergen_name

                if allergy_type:
                    allergy_type_system = self.code_mapping.cda_to_fhir(
                        allergy_type.codeSystem,
                        "system",
                        default="http://snomed.info/sct",
                    )
                    allergy.type = create_single_codeable_concept(
                        code=allergy_type.code,
                        display=allergy_type.displayName,
                        system=allergy_type_system,
                    )

                if reaction:
                    reaction_system = self.code_mapping.cda_to_fhir(
                        reaction.get("@codeSystem"),
                        "system",
                        default="http://snomed.info/sct",
                    )
                    allergy.reaction = create_single_reaction(
                        code=reaction.get("@code"),
                        display=reaction.get("@displayName"),
                        system=reaction_system,
                    )

                if severity:
                    severity_code = self.code_mapping.cda_to_fhir(
                        severity.get("@code"),
                        "severity",
                        default="http://snomed.info/sct",
                    )
                    if allergy.reaction:
                        allergy.reaction[0].severity = severity_code
                allergies.append(allergy)

        return allergies

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
        new_problem: Condition,
        timestamp: str,
        act_id: str,
        problem_reference_name: str,
    ) -> None:
        """
        Adds a new problem entry to the problem section of the CDA document.

        Args:
            new_problem (Condition): The new problem concept to be added.
            timestamp (str): The timestamp of the entry.
            act_id (str): The ID of the act.
            problem_reference_name (str): The reference name of the problem.

        Returns:
            None
        """

        # Get CDA status from FHIR clinical status
        fhir_status = new_problem.clinicalStatus.coding[0].code
        cda_status = self.code_mapping.fhir_to_cda(
            fhir_status, "status", case_sensitive=False, default="unknown"
        )

        # Get CDA system from FHIR system
        fhir_system = new_problem.code.coding[0].system
        cda_system = self.code_mapping.fhir_to_cda(
            fhir_system, "system", default="2.16.840.1.113883.6.96"
        )  # Default to SNOMED-CT

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
                "statusCode": {"@code": cda_status},
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
                            "@code": new_problem.code.coding[0].code,
                            "@codeSystem": cda_system,
                            "@displayName": new_problem.code.coding[0].display,
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
        self, problems: List[Condition], overwrite: bool = False
    ) -> None:
        """
        Adds a list of problem lists to the problems section.

        Args:
            problems (List[Condition]): A list of Condition resources to be added.
            overwrite (bool, optional): If True, the existing problem list will be overwritten.
                Defaults to False.

        Returns:
            None
        """
        if self._problem_section is None:
            log.warning(
                "Skipping: No problem section to add to, check your CDA configuration"
            )
            return

        timestamp = datetime.now().strftime(format="%Y%m%d")
        act_id = str(uuid.uuid4())
        problem_reference_name = "#p" + str(uuid.uuid4())[:8] + "name"

        if overwrite:
            self._problem_section.entry = []

        added_problems = []

        for problem in problems:
            if problem in self.problem_list:
                log.debug(
                    f"Skipping: Problem {problem.display_name} already exists in the problem list."
                )
                continue
            log.debug(f"Adding problem: {problem}")
            self._add_new_problem_entry(
                new_problem=problem,
                timestamp=timestamp,
                act_id=act_id,
                problem_reference_name=problem_reference_name,
            )
            added_problems.append(problem)

        if overwrite:
            self.problem_list = added_problems
        else:
            self.problem_list.extend(added_problems)

    def _add_new_medication_entry(
        self,
        new_medication: MedicationStatement,
        timestamp: str,
        subad_id: str,
        medication_reference_name: str,
    ) -> None:
        """
        Adds a new medication entry to the medication section of the CDA document.

        Args:
            new_medication (MedicationStatement): The FHIR MedicationStatement resource to add to the CDA
            timestamp (str): The timestamp for when this entry was created, in YYYYMMDD format
            subad_id (str): The unique ID for this substance administration entry
            medication_reference_name (str): The reference name used to link narrative text to this medication

        The method creates a CDA substance administration entry with:
        - Medication details (code, name, etc)
        - Dosage information if present (amount, route, frequency)
        - Effective time periods
        - Status as Active
        """

        # Get CDA system from FHIR system
        fhir_system = new_medication.medication.concept.coding[0].system
        cda_system = self.code_mapping.fhir_to_cda(
            fhir_system, "system", default="2.16.840.1.113883.6.96"
        )

        effective_times = []

        # Handle timing/frequency
        if new_medication.dosage and new_medication.dosage[0].timing:
            timing = new_medication.dosage[0].timing.repeat
            effective_times.append(
                {
                    "@xsi:type": "PIVL_TS",
                    "@institutionSpecified": True,
                    "@operator": "A",
                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "period": {
                        "@unit": timing.periodUnit,
                        "@value": str(timing.period),
                    },
                }
            )

        # Handle effective period
        # TODO: standardize datetime format
        if new_medication.effectivePeriod:
            time_range = {
                "@xsi:type": "IVL_TS",
                "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "low": {"@nullFlavor": "UNK"},
                "high": {"@nullFlavor": "UNK"},
            }
            if new_medication.effectivePeriod.start:
                time_range["low"] = {
                    "@value": CodeMapping.convert_date_fhir_to_cda(
                        new_medication.effectivePeriod.start
                    )
                }
            if new_medication.effectivePeriod.end:
                time_range["high"] = {
                    "@value": CodeMapping.convert_date_fhir_to_cda(
                        new_medication.effectivePeriod.end
                    )
                }
            effective_times.append(time_range)

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

        # Add dosage if present
        if new_medication.dosage and new_medication.dosage[0].doseAndRate:
            dose = new_medication.dosage[0].doseAndRate[0].doseQuantity
            template["substanceAdministration"]["doseQuantity"] = {
                "@value": dose.value,
                "@unit": dose.unit,
            }

        # Add route if present
        if new_medication.dosage and new_medication.dosage[0].route:
            route = new_medication.dosage[0].route.coding[0]
            route_system = self.code_mapping.fhir_to_cda(route.system, "system")
            template["substanceAdministration"]["routeCode"] = {
                "@code": route.code,
                "@codeSystem": route_system,
                "@displayName": route.display,
            }

        # Add timing
        if effective_times:
            template["substanceAdministration"]["effectiveTime"] = effective_times

        # Add medication details
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
                        "@code": new_medication.medication.concept.coding[0].code,
                        "@codeSystem": cda_system,
                        "@displayName": new_medication.medication.concept.coding[
                            0
                        ].display,
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

        if not isinstance(self._medication_section.entry, list):
            self._medication_section.entry = [self._medication_section.entry]

        new_entry = Entry(**template)
        self._medication_section.entry.append(new_entry)

    def add_to_medication_list(
        self, medications: List[MedicationStatement], overwrite: bool = False
    ) -> None:
        """
        Adds medications to the medication list.

        Args:
            medications (List[MedicationStatement]): A list of MedicationStatement resources to be added
            overwrite (bool, optional): If True, existing medication list will be overwritten. Defaults to False.
        """
        if self._medication_section is None:
            log.warning(
                "Skipping: No medication section to add to, check your CDA configuration"
            )
            return

        timestamp = datetime.now().strftime(format="%Y%m%d")
        subad_id = str(uuid.uuid4())
        medication_reference_name = "#m" + str(uuid.uuid4())[:8] + "name"

        if overwrite:
            self._medication_section.entry = []

        added_medications = []

        for medication in medications:
            if medication in self.medication_list:
                log.debug(
                    f"Skipping: medication {medication.medication.concept.coding[0].display} already exists in the medication list."
                )
                continue

            log.debug(f"Adding medication: {medication}")
            self._add_new_medication_entry(
                new_medication=medication,
                timestamp=timestamp,
                subad_id=subad_id,
                medication_reference_name=medication_reference_name,
            )
            added_medications.append(medication)

        if overwrite:
            self.medication_list = added_medications
        else:
            self.medication_list.extend(added_medications)

    def _add_new_allergy_entry(
        self,
        new_allergy: AllergyIntolerance,
        timestamp: str,
        act_id: str,
        allergy_reference_name: str,
    ) -> None:
        """
        Adds a new allergy entry to the allergy section of the CDA document.

        Args:
            new_allergy (AllergyIntolerance): The new allergy concept to be added.
            timestamp (str): The timestamp of the entry.
            act_id (str): The ID of the act.
            allergy_reference_name (str): The reference name of the allergy.

        Returns:
            None
        """

        # Get CDA system from FHIR system
        fhir_system = new_allergy.code.coding[0].system
        allergy_type__system = self.code_mapping.fhir_to_cda(
            fhir_system, "system", default="2.16.840.1.113883.6.96"
        )

        template = {
            "act": {
                "@classCode": "ACT",
                "@moodCode": "EVN",
                "templateId": [
                    {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.5.1"},
                    {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.5.3"},
                    {"@root": "2.16.840.1.113883.3.88.11.32.6"},
                    {"@root": "2.16.840.1.113883.3.88.11.83.6"},
                ],
                "id": {"@root": act_id},
                "code": {"@nullFlavor": "NA"},
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
                            {"@root": "1.3.6.1.4.1.19376.1.5.3.1.4.6"},
                            {"@root": "2.16.840.1.113883.10.20.1.18"},
                            {
                                "@root": "1.3.6.1.4.1.19376.1.5.3.1",
                                "@extension": "allergy",
                            },
                            {"@root": "2.16.840.1.113883.10.20.1.28"},
                        ],
                        "id": {"@root": act_id},
                        "text": {"reference": {"@value": allergy_reference_name}},
                        "statusCode": {"@code": "completed"},
                        "effectiveTime": {"low": {"@value": timestamp}},
                    },
                },
            }
        }
        allergen_observation = template["act"]["entryRelationship"]["observation"]

        # Attach allergy type code
        if new_allergy.type:
            allergy_type__system = self.code_mapping.fhir_to_cda(
                new_allergy.type.coding[0].system,
                "system",
                default="2.16.840.1.113883.6.96",
            )
            allergen_observation["code"] = {
                "@code": new_allergy.type.coding[0].code,
                "@codeSystem": allergy_type__system,
                # "@codeSystemName": new_allergy.type.coding[0].display,
                "@displayName": new_allergy.type.coding[0].display,
            }
        else:
            raise ValueError("Allergy type code cannot be missing when adding allergy.")

        # Attach allergen code to value and participant
        allergen_code_system = self.code_mapping.fhir_to_cda(
            new_allergy.code.coding[0].system,
            "system",
            default="2.16.840.1.113883.6.96",
        )
        allergen_observation["value"] = {
            "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "@code": new_allergy.code.coding[0].code,
            "@codeSystem": allergen_code_system,
            # "@codeSystemName": new_allergy.code.coding[0].display,
            "@displayName": new_allergy.code.coding[0].display,
            "originalText": {"reference": {"@value": allergy_reference_name}},
            "@xsi:type": "CD",
        }

        allergen_observation["participant"] = {
            "@typeCode": "CSM",
            "participantRole": {
                "@classCode": "MANU",
                "playingEntity": {
                    "@classCode": "MMAT",
                    "code": {
                        "originalText": {
                            "reference": {"@value": allergy_reference_name}
                        },
                        "@code": new_allergy.code.coding[0].code,
                        "@codeSystem": allergen_code_system,
                        # "@codeSystemName": new_allergy.code.coding[0].display,
                        "@displayName": new_allergy.code.coding[0].display,
                    },
                    "name": new_allergy.code.coding[0].display,
                },
            },
        }

        # We need an entryRelationship if either reaction or severity is present
        if new_allergy.reaction:
            allergen_observation["entryRelationship"] = {
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
                    ],
                    "id": {"@root": act_id},
                    "code": {"@code": "RXNASSESS"},
                    "text": {
                        "reference": {"@value": allergy_reference_name + "reaction"}
                    },
                    "statusCode": {"@code": "completed"},
                    "effectiveTime": {"low": {"@value": timestamp}},
                },
            }
            # Attach reaction code if given otherwise attach nullFlavor
            if new_allergy.reaction:
                reaction_code_system = self.code_mapping.fhir_to_cda(
                    new_allergy.reaction[0].manifestation[0].concept.coding[0].system,
                    "system",
                    default="2.16.840.1.113883.6.96",
                )
                allergen_observation["entryRelationship"]["observation"]["value"] = {
                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "@code": new_allergy.reaction[0]
                    .manifestation[0]
                    .concept.coding[0]
                    .code,
                    "@codeSystem": reaction_code_system,
                    # "@codeSystemName": new_allergy.reaction[0].manifestation[0].concept.coding[0].display,
                    "@displayName": new_allergy.reaction[0]
                    .manifestation[0]
                    .concept.coding[0]
                    .display,
                    "@xsi:type": "CD",
                    "originalText": {
                        "reference": {"@value": allergy_reference_name + "reaction"}
                    },
                }
            else:
                allergen_observation["entryRelationship"]["observation"]["value"] = {
                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "@nullFlavor": "OTH",
                    "@xsi:type": "CD",
                }
            # Attach severity code if given
            if new_allergy.reaction[0].severity:
                severity_code = self.code_mapping.fhir_to_cda(
                    new_allergy.reaction[0].severity, "severity"
                )
                allergen_observation["entryRelationship"]["observation"][
                    "entryRelationship"
                ] = {
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
                        "text": {
                            "reference": {"@value": allergy_reference_name + "severity"}
                        },
                        "statusCode": {"@code": "completed"},
                        "value": {
                            "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                            "@code": new_allergy.reaction[0].severity,
                            "@codeSystem": severity_code,
                            # "@codeSystemName": new_allergy.severity.code_system_name,
                            "@displayName": new_allergy.reaction[0].severity,
                            "@xsi:type": "CD",
                        },
                    },
                }

        if not isinstance(self._allergy_section.entry, list):
            self._allergy_section.entry = [self._allergy_section.entry]

        new_entry = Entry(**template)
        self._allergy_section.entry.append(new_entry)

    def add_to_allergy_list(
        self, allergies: List[AllergyIntolerance], overwrite: bool = False
    ) -> None:
        """
        Adds allergies to the allergy list.

        Args:
            allergies: List of FHIR AllergyIntolerance resources to add
            overwrite: If True, overwrites existing allergy list
        """
        if self._allergy_section is None:
            log.warning(
                "Skipping: No allergy section to add to, check your CDA configuration"
            )
            return

        timestamp = datetime.now().strftime(format="%Y%m%d")
        act_id = str(uuid.uuid4())
        allergy_reference_name = "#a" + str(uuid.uuid4())[:8] + "name"

        if overwrite:
            self._allergy_section.entry = []

        added_allergies = []

        for allergy in allergies:
            if allergy in self.allergy_list:
                log.debug(f"Allergy {allergy.code.coding[0].display} already exists")
                continue
            log.debug(f"Adding allergy: {allergy}")
            self._add_new_allergy_entry(
                new_allergy=allergy,
                timestamp=timestamp,
                act_id=act_id,
                allergy_reference_name=allergy_reference_name,
            )
            added_allergies.append(allergy)

        if overwrite:
            self.allergy_list = added_allergies
        else:
            self.allergy_list.extend(added_allergies)

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
