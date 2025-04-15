"""
DEPRECATED: These tests are for the CdaAnnotator class which is being deprecated.
The new InteropEngine should be used for CDA processing instead.
These tests are kept for reference and backward compatibility during the transition period.
"""

from healthchain.cda_parser.cdaannotator import (
    SectionId,
    SectionCode,
)
from fhir.resources.condition import Condition
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.medicationstatement import MedicationStatement


def test_find_notes_section(cda_annotator_with_data):
    # Test if the notes section is found correctly
    section = cda_annotator_with_data._find_notes_section()
    assert section is not None
    assert section.templateId.root == SectionId.NOTE.value


def test_find_notes_section_using_code(cda_annotator_without_template_id):
    # Test if the notes section is found correctly when no template_id is available in the document.
    section = cda_annotator_without_template_id._find_notes_section()
    assert section is not None
    assert section.code.code == SectionCode.NOTE.value


def test_find_problems_section(cda_annotator_with_data):
    section = cda_annotator_with_data._find_problems_section()
    assert section is not None
    assert section.templateId.root == SectionId.PROBLEM.value


def test_find_problems_section_using_code(cda_annotator_without_template_id):
    section = cda_annotator_without_template_id._find_problems_section()
    assert section is not None
    assert section.code.code == SectionCode.PROBLEM.value


def test_find_medications_section(cda_annotator_with_data):
    section = cda_annotator_with_data._find_medications_section()
    assert section is not None
    assert section.templateId[0].root == SectionId.MEDICATION.value


def test_find_medications_section_using_code(cda_annotator_without_template_id):
    section = cda_annotator_without_template_id._find_medications_section()
    assert section is not None
    assert section.code.code == SectionCode.MEDICATION.value


def test_find_allergies_section(cda_annotator_with_data):
    section = cda_annotator_with_data._find_allergies_section()
    assert section is not None
    assert section.templateId[0].root == SectionId.ALLERGY.value


def test_find_allergies_section_using_code(cda_annotator_without_template_id):
    section = cda_annotator_without_template_id._find_allergies_section()
    assert section is not None
    assert section.code.code == SectionCode.ALLERGY.value


def test_extract_note(cda_annotator_with_data):
    # Test if the note is extracted correctly
    note = cda_annotator_with_data._extract_note()
    assert note == {"paragraph": "test"}


def test_extract_note_using_code(cda_annotator_without_template_id):
    # Test if the note is extracted correctly
    note = cda_annotator_without_template_id._extract_note()
    assert note == {"paragraph": "test"}


def test_extract_problems_to_fhir(cda_annotator_with_data):
    """Test if problems are extracted correctly as FHIR Condition resources"""
    problems = cda_annotator_with_data._extract_problems()
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


def test_extract_problems_using_code(cda_annotator_without_template_id):
    """Test if problems are extracted correctly from code-based sections as FHIR Condition resources"""
    problems = cda_annotator_without_template_id._extract_problems()
    assert len(problems) > 0
    for problem in problems:
        assert isinstance(problem, Condition)
        assert isinstance(problem.code, CodeableConcept)
        assert isinstance(problem.code.coding[0], Coding)


def test_extract_medications_to_fhir(cda_annotator_with_data):
    """Test if medications are extracted correctly as FHIR MedicationStatement resources"""
    medications = cda_annotator_with_data._extract_medications()
    assert len(medications) == 1

    med = medications[0]
    assert isinstance(med, MedicationStatement)

    # Check medication code
    assert med.medication.concept.coding[0].code == "314076"
    assert (
        med.medication.concept.coding[0].system
        == "http://www.nlm.nih.gov/research/umls/rxnorm"
    )
    assert med.medication.concept.coding[0].display == "lisinopril 10 MG Oral Tablet"

    # Check dosage
    assert med.dosage[0].doseAndRate[0].doseQuantity.value == 30.0
    assert med.dosage[0].doseAndRate[0].doseQuantity.unit == "mg"

    # Check route
    assert med.dosage[0].route.coding[0].code == "C38288"
    assert med.dosage[0].route.coding[0].system == "http://ncit.nci.nih.gov"
    assert med.dosage[0].route.coding[0].display == "Oral"

    # Check timing
    assert med.dosage[0].timing.repeat.period == 0.5
    assert med.dosage[0].timing.repeat.periodUnit == "d"

    # Check period
    assert med.effectivePeriod.end == "2022-10-20"


def test_extract_medications_using_code(cda_annotator_without_template_id):
    """Test extracting medications from code-based sections"""
    medications = cda_annotator_without_template_id._extract_medications()
    assert len(medications) == 1

    med = medications[0]
    assert isinstance(med, MedicationStatement)

    # Check basic medication details
    assert med.medication.concept.coding[0].code == "314076"
    assert (
        med.medication.concept.coding[0].system
        == "http://www.nlm.nih.gov/research/umls/rxnorm"
    )
    assert med.medication.concept.coding[0].display == "lisinopril 10 MG Oral Tablet"


def test_extract_allergies_to_fhir(cda_annotator_with_data):
    allergies = cda_annotator_with_data._extract_allergies()

    assert len(allergies) == 1
    assert allergies[0].code.coding[0].code == "102263004"
    assert allergies[0].code.coding[0].system == "http://snomed.info/sct"
    assert allergies[0].code.coding[0].display == "EGGS"

    assert allergies[0].type.coding[0].code == "418471000"
    assert allergies[0].type.coding[0].system == "http://snomed.info/sct"
    assert (
        allergies[0].type.coding[0].display == "Propensity to adverse reactions to food"
    )

    assert (
        allergies[0].reaction[0].manifestation[0].concept.coding[0].code == "65124004"
    )
    assert (
        allergies[0].reaction[0].manifestation[0].concept.coding[0].system
        == "http://snomed.info/sct"
    )
    assert (
        allergies[0].reaction[0].manifestation[0].concept.coding[0].display
        == "Swelling"
    )
    assert allergies[0].reaction[0].severity == "severe"


def test_extract_allergies_using_code(cda_annotator_without_template_id):
    allergies = cda_annotator_without_template_id._extract_allergies()

    assert len(allergies) == 1
    assert allergies[0].code.coding[0].code == "102263004"
    assert allergies[0].code.coding[0].system == "http://snomed.info/sct"
    assert allergies[0].code.coding[0].display == "EGGS"


def test_add_to_empty_sections(
    cda_annotator_with_data, test_condition, test_medication, test_allergy
):
    cda_annotator_with_data._problem_section = None
    cda_annotator_with_data.problem_list = []
    cda_annotator_with_data.add_to_problem_list(test_condition)
    assert cda_annotator_with_data.problem_list == []

    cda_annotator_with_data._medication_section = None
    cda_annotator_with_data.medication_list = []
    cda_annotator_with_data.add_to_medication_list(test_medication)
    assert cda_annotator_with_data.medication_list == []

    cda_annotator_with_data._allergy_section = None
    cda_annotator_with_data.allergy_list = []
    cda_annotator_with_data.add_to_allergy_list(test_allergy)
    assert cda_annotator_with_data.allergy_list == []


def test_add_to_problem_list(cda_annotator_with_data, test_condition):
    """Test adding FHIR Conditions to the problem list"""

    cda_annotator_with_data.add_to_problem_list([test_condition])
    assert len(cda_annotator_with_data.problem_list) == 2
    assert test_condition in cda_annotator_with_data.problem_list


def test_add_to_problem_list_overwrite(cda_annotator_with_data, test_condition):
    """Test overwriting problem list with new FHIR Conditions"""
    cda_annotator_with_data.add_to_problem_list([test_condition], overwrite=True)
    assert len(cda_annotator_with_data.problem_list) == 1
    assert test_condition in cda_annotator_with_data.problem_list


def test_add_multiple_to_problem_list(cda_annotator_with_data, test_condition):
    """Test adding multiple FHIR Conditions to the problem list"""
    cda_annotator_with_data.add_to_problem_list([test_condition, test_condition])
    assert len(cda_annotator_with_data.problem_list) == 3
    assert test_condition in cda_annotator_with_data.problem_list


def test_add_multiple_to_problem_list_overwrite(
    cda_annotator_with_data, test_condition
):
    """Test overwriting problem list with new FHIR Conditions"""
    cda_annotator_with_data.add_to_problem_list(
        [test_condition, test_condition], overwrite=True
    )
    assert len(cda_annotator_with_data.problem_list) == 2
    assert test_condition in cda_annotator_with_data.problem_list


def test_add_to_medication_list(cda_annotator_with_data, test_medication):
    """Test adding medications to the medication list"""
    initial_count = len(cda_annotator_with_data.medication_list)

    # Add medication
    cda_annotator_with_data.add_to_medication_list([test_medication])

    # Check medication was added
    assert len(cda_annotator_with_data.medication_list) == initial_count + 1
    assert test_medication in cda_annotator_with_data.medication_list

    # Try adding same medication again
    cda_annotator_with_data.add_to_medication_list([test_medication])

    # Check duplicate was not added
    assert len(cda_annotator_with_data.medication_list) == initial_count + 1


def test_add_to_medication_list_overwrite(cda_annotator_with_data, test_medication):
    """Test overwriting the medication list"""
    # Add medication with overwrite
    cda_annotator_with_data.add_to_medication_list([test_medication], overwrite=True)

    # Check only new medication exists
    assert len(cda_annotator_with_data.medication_list) == 1
    assert test_medication in cda_annotator_with_data.medication_list


def test_add_to_allergy_list(cda_annotator_with_data, test_allergy_with_reaction):
    # Test if allergies are added to the allergy list correctly with overwrite=True
    cda_annotator_with_data.add_to_allergy_list([test_allergy_with_reaction])
    assert len(cda_annotator_with_data.allergy_list) == 2
    assert len(cda_annotator_with_data._allergy_section.entry) == 2


def test_add_to_allergy_list_overwrite(
    cda_annotator_with_data, test_allergy_with_reaction
):
    cda_annotator_with_data.add_to_allergy_list(
        [test_allergy_with_reaction], overwrite=True
    )
    assert len(cda_annotator_with_data.allergy_list) == 1
    assert len(cda_annotator_with_data._allergy_section.entry) == 1


def test_export_pretty_print(cda_annotator_with_data):
    # Test if the export function returns a valid string with pretty_print=True
    exported_data = cda_annotator_with_data.export(pretty_print=True)
    assert isinstance(exported_data, str)
    assert "\t" in exported_data


def test_export_no_pretty_print(cda_annotator_with_data):
    # Test if the export function returns a valid string with pretty_print=False
    exported_data = cda_annotator_with_data.export(pretty_print=False)
    assert isinstance(exported_data, str)


def test_add_new_problem_entry(cda_annotator_with_data, test_condition):
    """Test if a new FHIR Condition entry is added correctly to CDA structure"""

    timestamp = "20220101"
    act_id = "12345678"
    problem_reference_name = "#p12345678name"

    cda_annotator_with_data._add_new_problem_entry(
        new_problem=test_condition,
        timestamp=timestamp,
        act_id=act_id,
        problem_reference_name=problem_reference_name,
    )

    assert len(cda_annotator_with_data._problem_section.entry) == 2
    assert cda_annotator_with_data._problem_section.entry[1].act.id.root == act_id
    assert (
        cda_annotator_with_data._problem_section.entry[1].act.effectiveTime.low.value
        == timestamp
    )
    assert cda_annotator_with_data._problem_section.entry[
        1
    ].act.entryRelationship.observation.text == {
        "reference": {"@value": problem_reference_name}
    }
    assert cda_annotator_with_data._problem_section.entry[
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
        cda_annotator_with_data._problem_section.entry[
            1
        ].act.entryRelationship.observation.effectiveTime.low.value
        == timestamp
    )
    assert (
        cda_annotator_with_data._problem_section.entry[
            1
        ].act.entryRelationship.observation.entryRelationship.observation.effectiveTime.low.value
        == timestamp
    )


def test_add_new_medication_entry(cda_annotator_with_data, test_medication_with_dosage):
    # Test if a new medication entry is added correctly

    timestamp = "20240701"
    subad_id = "12345678"
    med_reference_name = "#m12345678name"

    cda_annotator_with_data._add_new_medication_entry(
        new_medication=test_medication_with_dosage,
        timestamp=timestamp,
        subad_id=subad_id,
        medication_reference_name=med_reference_name,
    )

    assert len(cda_annotator_with_data._medication_section.entry) == 2

    subad = cda_annotator_with_data._medication_section.entry[1].substanceAdministration
    assert subad.id.root == subad_id

    # Check dosage
    assert subad.doseQuantity.value == 500
    assert subad.doseQuantity.unit == "mg"

    # Check route
    assert subad.routeCode.code == "test"
    assert subad.routeCode.displayName == "test"

    # Check timing
    assert subad.effectiveTime[0] == {
        "@xsi:type": "PIVL_TS",
        "@institutionSpecified": True,
        "@operator": "A",
        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "period": {
            "@unit": "d",
            "@value": "1",
        },
    }

    # Check period
    assert subad.effectiveTime[1] == {
        "@xsi:type": "IVL_TS",
        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "low": {"@nullFlavor": "UNK"},
        "high": {"@value": "20221020"},
    }

    # Check medication details
    consumable_code = subad.consumable.manufacturedProduct.manufacturedMaterial.code
    assert consumable_code.code == "456"
    assert consumable_code.displayName == "Test Medication"
    assert consumable_code.codeSystem == "2.16.840.1.113883.6.96"
    assert consumable_code.originalText == {"reference": {"@value": med_reference_name}}

    assert subad.entryRelationship[0].observation.effectiveTime.low.value == timestamp


def test_add_new_allergy_entry(cda_annotator_with_data, test_allergy_with_reaction):
    timestamp = "20220101"
    act_id = "12345678"
    allergy_reference_name = "#a12345678name"

    cda_annotator_with_data._add_new_allergy_entry(
        new_allergy=test_allergy_with_reaction,
        timestamp=timestamp,
        act_id=act_id,
        allergy_reference_name=allergy_reference_name,
    )

    assert len(cda_annotator_with_data._allergy_section.entry) == 2
    assert cda_annotator_with_data._allergy_section.entry[1].act.id.root == act_id
    assert (
        cda_annotator_with_data._allergy_section.entry[1].act.effectiveTime.low.value
        == timestamp
    )
    allergen_observation = cda_annotator_with_data._allergy_section.entry[
        1
    ].act.entryRelationship.observation
    assert allergen_observation.id.root == act_id
    assert allergen_observation.text == {
        "reference": {"@value": allergy_reference_name}
    }
    assert allergen_observation.effectiveTime.low.value == timestamp
    assert allergen_observation.code.code == "ABC"
    assert allergen_observation.code.codeSystem == "2.16.840.1.113883.6.96"
    assert allergen_observation.value == {
        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "@code": test_allergy_with_reaction.code.coding[0].code,
        "@codeSystem": "2.16.840.1.113883.6.96",
        "@displayName": test_allergy_with_reaction.code.coding[0].display,
        "originalText": {"reference": {"@value": allergy_reference_name}},
        "@xsi:type": "CD",
    }
    assert (
        allergen_observation.participant.participantRole.playingEntity.code.code
        == test_allergy_with_reaction.code.coding[0].code
    )
    assert (
        allergen_observation.participant.participantRole.playingEntity.code.codeSystem
        == "2.16.840.1.113883.6.96"
    )
    assert (
        allergen_observation.participant.participantRole.playingEntity.code.displayName
        == test_allergy_with_reaction.code.coding[0].display
    )
    assert (
        allergen_observation.participant.participantRole.playingEntity.code.displayName
        == test_allergy_with_reaction.code.coding[0].display
    )

    assert allergen_observation.entryRelationship.observation.value["@code"] == "DEF"
    assert (
        allergen_observation.entryRelationship.observation.entryRelationship.observation.value[
            "@code"
        ]
        == "GHI"
    )

    assert (
        cda_annotator_with_data._allergy_section.entry[
            1
        ].act.entryRelationship.observation.entryRelationship.observation.entryRelationship.observation.value[
            "@code"
        ]
        == "GHI"
    )
