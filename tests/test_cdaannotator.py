import pytest
from healthchain.cda_parser.cdaannotator import (
    SectionId,
    SectionCode,
    AllergyConcept,
)
from healthchain.models.data.concept import (
    Concept,
    MedicationConcept,
    Quantity,
    Range,
    TimeInterval,
)
from fhir.resources.condition import Condition
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding


@pytest.fixture
def test_condition():
    return Condition(
        subject={"reference": "Patient/123"},
        code=CodeableConcept(
            coding=[
                Coding(
                    system="http://snomed.info/sct",
                    code="123456",
                    display="Test Condition",
                )
            ]
        ),
        clinicalStatus=CodeableConcept(
            coding=[
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                    code="active",
                    display="Active",
                )
            ]
        ),
    )


def test_find_notes_section(cda_annotator):
    # Test if the notes section is found correctly
    section = cda_annotator._find_notes_section()
    assert section is not None
    assert section.templateId.root == SectionId.NOTE.value


def test_find_notes_section_using_code(cda_annotator_code):
    # Test if the notes section is found correctly when no template_id is available in the document.
    section = cda_annotator_code._find_notes_section()
    assert section is not None
    assert section.code.code == SectionCode.NOTE.value


def test_find_problems_section(cda_annotator):
    section = cda_annotator._find_problems_section()
    assert section is not None
    assert section.templateId.root == SectionId.PROBLEM.value


def test_find_problems_section_using_code(cda_annotator_code):
    section = cda_annotator_code._find_problems_section()
    assert section is not None
    assert section.code.code == SectionCode.PROBLEM.value


def test_find_medications_section(cda_annotator):
    section = cda_annotator._find_medications_section()
    assert section is not None
    assert section.templateId[0].root == SectionId.MEDICATION.value


def test_find_medications_section_using_code(cda_annotator_code):
    section = cda_annotator_code._find_medications_section()
    assert section is not None
    assert section.code.code == SectionCode.MEDICATION.value


def test_find_allergies_section(cda_annotator):
    section = cda_annotator._find_allergies_section()
    assert section is not None
    assert section.templateId[0].root == SectionId.ALLERGY.value


def test_find_allergies_section_using_code(cda_annotator_code):
    section = cda_annotator_code._find_allergies_section()
    assert section is not None
    assert section.code.code == SectionCode.ALLERGY.value


def test_extract_note(cda_annotator):
    # Test if the note is extracted correctly
    note = cda_annotator._extract_note()
    assert note == {"paragraph": "test"}


def test_extract_note_using_code(cda_annotator_code):
    # Test if the note is extracted correctly
    note = cda_annotator_code._extract_note()
    assert note == {"paragraph": "test"}


def test_extract_problems(cda_annotator):
    """Test if problems are extracted correctly as FHIR Condition resources"""
    problems = cda_annotator._extract_problems()
    assert len(problems) > 0
    for problem in problems:
        assert isinstance(problem, Condition)
        assert isinstance(problem.code, CodeableConcept)
        assert isinstance(problem.code.coding[0], Coding)
        assert problem.code.coding[0].system == "http://snomed.info/sct"
        assert problem.code.coding[0].code == "38341003"
        assert problem.clinicalStatus.coding[0].code == "active"
        assert problem.subject.reference == "Patient/123"
        assert problem.onsetDateTime == "2021-03-17"
        assert problem.category[0].coding[0].code == "problem-list-item"


def test_extract_problems_using_code(cda_annotator_code):
    """Test if problems are extracted correctly from code-based sections as FHIR Condition resources"""
    problems = cda_annotator_code._extract_problems()
    assert len(problems) > 0
    for problem in problems:
        assert isinstance(problem, Condition)
        assert isinstance(problem.code, CodeableConcept)
        assert isinstance(problem.code.coding[0], Coding)


def test_extract_medications(cda_annotator):
    medications = cda_annotator._extract_medications()

    assert len(medications) == 1
    assert medications[0].code == "314076"
    assert medications[0].code_system == "2.16.840.1.113883.6.88"
    assert medications[0].display_name == "lisinopril 10 MG Oral Tablet"

    assert medications[0].dosage.value == 30.0
    assert medications[0].dosage.unit == "mg"

    assert medications[0].route.code == "C38288"
    assert medications[0].route.code_system == "2.16.840.1.113883.3.26.1.1"
    assert medications[0].route.code_system_name == "NCI Thesaurus"
    assert medications[0].route.display_name == "Oral"

    assert medications[0].frequency.period.value == 0.5
    assert medications[0].frequency.period.unit == "d"
    assert medications[0].frequency.institution_specified

    assert medications[0].duration.low is None
    assert medications[0].duration.high.value == 20221020

    assert medications[0].precondition == {
        "@typeCode": "PRCN",
        "criterion": {
            "templateId": [
                {"@root": "2.16.840.1.113883.10.20.22.4.25"},
                {
                    "@extension": "2014-06-09",
                    "@root": "2.16.840.1.113883.10.20.22.4.25",
                },
            ],
            "code": {"@code": "ASSERTION", "@codeSystem": "2.16.840.1.113883.5.4"},
            "value": {
                "@nullFlavor": "NI",
                "@xsi:type": "CD",
                "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            },
        },
    }


def test_extract_medications_using_code(cda_annotator_code):
    medications = cda_annotator_code._extract_medications()

    assert len(medications) == 1
    assert medications[0].code == "314076"
    assert medications[0].code_system == "2.16.840.1.113883.6.88"
    assert medications[0].display_name == "lisinopril 10 MG Oral Tablet"

    assert medications[0].dosage.value == 30.0
    assert medications[0].dosage.unit == "mg"

    assert medications[0].route.code == "C38288"
    assert medications[0].route.code_system == "2.16.840.1.113883.3.26.1.1"
    assert medications[0].route.code_system_name == "NCI Thesaurus"
    assert medications[0].route.display_name == "Oral"

    assert medications[0].frequency.period.value == 0.5
    assert medications[0].frequency.period.unit == "d"
    assert medications[0].frequency.institution_specified

    assert medications[0].duration.low is None
    assert medications[0].duration.high.value == 20221020

    assert medications[0].precondition == {
        "@typeCode": "PRCN",
        "criterion": {
            "templateId": [
                {"@root": "2.16.840.1.113883.10.20.22.4.25"},
                {
                    "@extension": "2014-06-09",
                    "@root": "2.16.840.1.113883.10.20.22.4.25",
                },
            ],
            "code": {"@code": "ASSERTION", "@codeSystem": "2.16.840.1.113883.5.4"},
            "value": {
                "@nullFlavor": "NI",
                "@xsi:type": "CD",
                "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            },
        },
    }


def test_extract_allergies(cda_annotator):
    allergies = cda_annotator._extract_allergies()

    assert len(allergies) == 1
    assert allergies[0].code == "102263004"
    assert allergies[0].code_system == "2.16.840.1.113883.6.96"
    assert allergies[0].code_system_name == "SNOMED-CT"
    assert allergies[0].display_name == "EGGS"
    assert allergies[0].allergy_type.code == "418471000"
    assert allergies[0].allergy_type.code_system == "2.16.840.1.113883.6.96"
    assert allergies[0].allergy_type.code_system_name == "SNOMED CT"
    assert (
        allergies[0].allergy_type.display_name
        == "Propensity to adverse reactions to food"
    )
    assert allergies[0].reaction.code == "65124004"
    assert allergies[0].reaction.code_system == "2.16.840.1.113883.6.96"
    assert allergies[0].reaction.code_system_name == "SNOMED CT"
    assert allergies[0].reaction.display_name == "Swelling"
    assert allergies[0].severity.code == "H"
    assert allergies[0].severity.code_system == "2.16.840.1.113883.5.1063"
    assert allergies[0].severity.code_system_name == "SeverityObservation"
    assert allergies[0].severity.display_name == "High"


def test_extract_allergies_using_code(cda_annotator_code):
    allergies = cda_annotator_code._extract_allergies()

    assert len(allergies) == 1
    assert allergies[0].code == "102263004"
    assert allergies[0].code_system == "2.16.840.1.113883.6.96"
    assert allergies[0].code_system_name == "SNOMED-CT"
    assert allergies[0].display_name == "EGGS"
    assert allergies[0].allergy_type.code == "418471000"
    assert allergies[0].allergy_type.code_system == "2.16.840.1.113883.6.96"
    assert allergies[0].allergy_type.code_system_name == "SNOMED CT"
    assert (
        allergies[0].allergy_type.display_name
        == "Propensity to adverse reactions to food"
    )
    assert allergies[0].reaction.code == "65124004"
    assert allergies[0].reaction.code_system == "2.16.840.1.113883.6.96"
    assert allergies[0].reaction.code_system_name == "SNOMED CT"
    assert allergies[0].reaction.display_name == "Swelling"
    assert allergies[0].severity.code == "H"
    assert allergies[0].severity.code_system == "2.16.840.1.113883.5.1063"
    assert allergies[0].severity.code_system_name == "SeverityObservation"
    assert allergies[0].severity.display_name == "High"


def test_add_to_empty_sections(cda_annotator, test_ccd_data):
    cda_annotator._problem_section = None
    cda_annotator.problem_list = []
    cda_annotator.add_to_problem_list(test_ccd_data.concepts.problems)
    assert cda_annotator.problem_list == []

    cda_annotator._medication_section = None
    cda_annotator.medication_list = []
    cda_annotator.add_to_medication_list(test_ccd_data.concepts.medications)
    assert cda_annotator.medication_list == []

    cda_annotator._allergy_section = None
    cda_annotator.allergy_list = []
    cda_annotator.add_to_allergy_list(test_ccd_data.concepts.allergies)
    assert cda_annotator.allergy_list == []


def test_add_to_problem_list(cda_annotator, test_condition):
    """Test adding FHIR Conditions to the problem list"""

    cda_annotator.add_to_problem_list([test_condition])
    assert len(cda_annotator.problem_list) == 2
    assert test_condition in cda_annotator.problem_list


def test_add_to_problem_list_overwrite(cda_annotator, test_condition):
    """Test overwriting problem list with new FHIR Conditions"""
    cda_annotator.add_to_problem_list([test_condition], overwrite=True)
    assert len(cda_annotator.problem_list) == 1
    assert test_condition in cda_annotator.problem_list


def test_add_multiple_to_problem_list(cda_annotator, test_condition):
    """Test adding multiple FHIR Conditions to the problem list"""
    cda_annotator.add_to_problem_list([test_condition, test_condition])
    assert len(cda_annotator.problem_list) == 3
    assert test_condition in cda_annotator.problem_list


def test_add_multiple_to_problem_list_overwrite(cda_annotator, test_condition):
    """Test overwriting problem list with new FHIR Conditions"""
    cda_annotator.add_to_problem_list([test_condition, test_condition], overwrite=True)
    assert len(cda_annotator.problem_list) == 2
    assert test_condition in cda_annotator.problem_list


def test_add_to_medication_list(cda_annotator, test_ccd_data):
    medications = test_ccd_data.concepts.medications
    cda_annotator.add_to_medication_list(medications)
    assert len(cda_annotator.medication_list) == 2
    assert len(cda_annotator._medication_section.entry) == 2


def test_add_to_medication_list_overwrite(cda_annotator, test_ccd_data):
    # Test if medications are added to the medication list correctly with overwrite=True
    medications = test_ccd_data.concepts.medications
    cda_annotator.add_to_medication_list(medications, overwrite=True)
    assert len(cda_annotator.medication_list) == 1
    assert len(cda_annotator._medication_section.entry) == 1


def test_add_multiple_to_medication_list(cda_annotator, test_multiple_ccd_data):
    medications = test_multiple_ccd_data.concepts.medications
    cda_annotator.add_to_medication_list(medications)
    assert len(cda_annotator.medication_list) == 3
    assert len(cda_annotator._medication_section.entry) == 3

    # Test deduplicate
    cda_annotator.add_to_medication_list(medications)
    assert len(cda_annotator.medication_list) == 3
    assert len(cda_annotator._medication_section.entry) == 3


def test_add_multiple_to_medication_list_overwrite(
    cda_annotator, test_multiple_ccd_data
):
    medications = test_multiple_ccd_data.concepts.medications
    cda_annotator.add_to_medication_list(medications, overwrite=True)
    assert len(cda_annotator.medication_list) == 2
    assert len(cda_annotator._medication_section.entry) == 2


def test_add_to_allergy_list(cda_annotator, test_ccd_data):
    # Test if allergies are added to the allergy list correctly with overwrite=True
    allergies = test_ccd_data.concepts.allergies
    cda_annotator.add_to_allergy_list(allergies)
    assert len(cda_annotator.allergy_list) == 2
    assert len(cda_annotator._allergy_section.entry) == 2


def test_add_to_allergy_list_overwrite(cda_annotator, test_ccd_data):
    allergies = test_ccd_data.concepts.allergies
    cda_annotator.add_to_allergy_list(allergies, overwrite=True)
    assert len(cda_annotator.allergy_list) == 1
    assert len(cda_annotator._allergy_section.entry) == 1


def test_add_multiple_to_allergy_list(cda_annotator, test_multiple_ccd_data):
    # Test if allergies are added to the allergy list correctly with overwrite=True
    allergies = test_multiple_ccd_data.concepts.allergies
    cda_annotator.add_to_allergy_list(allergies)
    assert len(cda_annotator.allergy_list) == 3
    assert len(cda_annotator._allergy_section.entry) == 3

    cda_annotator.add_to_allergy_list(allergies)
    assert len(cda_annotator.allergy_list) == 3
    assert len(cda_annotator._allergy_section.entry) == 3


def test_add_multiple_to_allergy_list_overwrite(cda_annotator, test_multiple_ccd_data):
    allergies = test_multiple_ccd_data.concepts.allergies
    cda_annotator.add_to_allergy_list(allergies, overwrite=True)
    assert len(cda_annotator.allergy_list) == 2
    assert len(cda_annotator._allergy_section.entry) == 2


def test_export_pretty_print(cda_annotator):
    # Test if the export function returns a valid string with pretty_print=True
    exported_data = cda_annotator.export(pretty_print=True)
    assert isinstance(exported_data, str)
    assert "\t" in exported_data


def test_export_no_pretty_print(cda_annotator):
    # Test if the export function returns a valid string with pretty_print=False
    exported_data = cda_annotator.export(pretty_print=False)
    assert isinstance(exported_data, str)


def test_add_new_problem_entry(cda_annotator, test_condition):
    """Test if a new FHIR Condition entry is added correctly to CDA structure"""

    timestamp = "20220101"
    act_id = "12345678"
    problem_reference_name = "#p12345678name"

    cda_annotator._add_new_problem_entry(
        new_problem=test_condition,
        timestamp=timestamp,
        act_id=act_id,
        problem_reference_name=problem_reference_name,
    )

    assert len(cda_annotator._problem_section.entry) == 2
    assert cda_annotator._problem_section.entry[1].act.id.root == act_id
    assert (
        cda_annotator._problem_section.entry[1].act.effectiveTime.low.value == timestamp
    )
    assert cda_annotator._problem_section.entry[
        1
    ].act.entryRelationship.observation.text == {
        "reference": {"@value": problem_reference_name}
    }
    assert cda_annotator._problem_section.entry[
        1
    ].act.entryRelationship.observation.value == {
        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "@code": test_condition.code.coding[0].code,
        "@codeSystem": "2.16.840.1.113883.6.96",
        "@displayName": test_condition.code.coding[0].display,
        "originalText": {"reference": {"@value": problem_reference_name}},
        "@xsi:type": "CD",
    }
    assert (
        cda_annotator._problem_section.entry[
            1
        ].act.entryRelationship.observation.effectiveTime.low.value
        == timestamp
    )
    assert (
        cda_annotator._problem_section.entry[
            1
        ].act.entryRelationship.observation.entryRelationship.observation.effectiveTime.low.value
        == timestamp
    )


def test_add_new_medication_entry(cda_annotator):
    # Test if a new medication entry is added correctly
    new_med = MedicationConcept()
    new_med.code = "12345678"
    new_med.code_system = "2.16.840.1.113883.6.96"
    new_med.code_system_name = "SNOMED CT"
    new_med.display_name = "Test Medication"
    new_med.dosage = Quantity(**{"value": 500, "unit": "mg"})
    new_med.route = Concept(
        **{"code": "test", "code_system": "2.16.840.1.113883", "display_name": "test"}
    )
    new_med.frequency = TimeInterval(
        **{
            "period": Quantity(**{"value": 1, "unit": "d"}),
            "institution_specified": True,
        }
    )
    new_med.duration = Range(**{"high": Quantity(**{"value": "20221020"})})
    timestamp = "20240701"
    subad_id = "12345678"
    med_reference_name = "#m12345678name"

    cda_annotator._add_new_medication_entry(
        new_medication=new_med,
        timestamp=timestamp,
        subad_id=subad_id,
        medication_reference_name=med_reference_name,
    )
    assert len(cda_annotator._medication_section.entry) == 2

    subad = cda_annotator._medication_section.entry[1].substanceAdministration

    assert subad.id.root == subad_id

    assert subad.doseQuantity.value == new_med.dosage.value
    assert subad.doseQuantity.unit == new_med.dosage.unit

    assert subad.routeCode.code == new_med.route.code
    assert subad.routeCode.codeSystem == new_med.route.code_system
    assert subad.routeCode.displayName == new_med.route.display_name

    assert subad.effectiveTime[0] == {
        "@xsi:type": "PIVL_TS",
        "@institutionSpecified": new_med.frequency.institution_specified,
        "@operator": "A",
        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "period": {
            "@unit": new_med.frequency.period.unit,
            "@value": new_med.frequency.period.value,
        },
    }
    assert subad.effectiveTime[1] == {
        "@xsi:type": "IVL_TS",
        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "low": {"@nullFlavor": "UNK"},
        "high": {"@value": new_med.duration.high.value},
    }

    consumable_code = subad.consumable.manufacturedProduct.manufacturedMaterial.code

    assert consumable_code.code == new_med.code
    assert consumable_code.codeSystem == new_med.code_system
    assert consumable_code.codeSystemName == new_med.code_system_name
    assert consumable_code.displayName == new_med.display_name
    assert consumable_code.originalText == {"reference": {"@value": med_reference_name}}

    assert subad.entryRelationship[0].observation.effectiveTime.low.value == timestamp


def test_add_new_allergy_entry(cda_annotator):
    # Test if a new problem entry is added correctly
    new_allergy = AllergyConcept()
    new_allergy.code = "12345678"
    new_allergy.code_system = "2.16.840.1.113883.6.96"
    new_allergy.code_system_name = "SNOMED CT"
    new_allergy.display_name = "Test Allergy"
    new_allergy.allergy_type = Concept(**{"code": "ABC", "code_system": "snomed"})
    new_allergy.reaction = Concept(**{"code": "DEF"})
    new_allergy.severity = Concept(**{"code": "GHI"})
    timestamp = "20220101"
    act_id = "12345678"
    allergy_reference_name = "#a12345678name"

    cda_annotator._add_new_allergy_entry(
        new_allergy=new_allergy,
        timestamp=timestamp,
        act_id=act_id,
        allergy_reference_name=allergy_reference_name,
    )

    assert len(cda_annotator._allergy_section.entry) == 2
    assert cda_annotator._allergy_section.entry[1].act.id.root == act_id
    assert (
        cda_annotator._allergy_section.entry[1].act.effectiveTime.low.value == timestamp
    )
    allergen_observation = cda_annotator._allergy_section.entry[
        1
    ].act.entryRelationship.observation
    assert allergen_observation.id.root == act_id
    assert allergen_observation.text == {
        "reference": {"@value": allergy_reference_name}
    }
    assert allergen_observation.effectiveTime.low.value == timestamp
    assert allergen_observation.code.code == "ABC"
    assert allergen_observation.code.codeSystem == "snomed"
    assert allergen_observation.value == {
        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "@code": new_allergy.code,
        "@codeSystem": new_allergy.code_system,
        "@codeSystemName": new_allergy.code_system_name,
        "@displayName": new_allergy.display_name,
        "originalText": {"reference": {"@value": allergy_reference_name}},
        "@xsi:type": "CD",
    }
    assert (
        allergen_observation.participant.participantRole.playingEntity.code.code
        == new_allergy.code
    )
    assert (
        allergen_observation.participant.participantRole.playingEntity.code.codeSystem
        == new_allergy.code_system
    )
    assert (
        allergen_observation.participant.participantRole.playingEntity.code.codeSystemName
        == new_allergy.code_system_name
    )
    assert (
        allergen_observation.participant.participantRole.playingEntity.code.displayName
        == new_allergy.display_name
    )
    assert (
        allergen_observation.participant.participantRole.playingEntity.name
        == new_allergy.display_name
    )

    assert allergen_observation.entryRelationship.observation.value["@code"] == "DEF"
    assert (
        allergen_observation.entryRelationship.observation.entryRelationship.observation.value[
            "@code"
        ]
        == "GHI"
    )

    # Test adding withhout a reaction
    new_allergy.reaction = None
    cda_annotator._add_new_allergy_entry(
        new_allergy=new_allergy,
        timestamp=timestamp,
        act_id=act_id,
        allergy_reference_name=allergy_reference_name,
    )
    assert (
        cda_annotator._allergy_section.entry[
            2
        ].act.entryRelationship.observation.entryRelationship.observation.value[
            "@nullFlavor"
        ]
        == "OTH"
    )
    assert (
        cda_annotator._allergy_section.entry[
            2
        ].act.entryRelationship.observation.entryRelationship.observation.entryRelationship.observation.value[
            "@code"
        ]
        == "GHI"
    )
