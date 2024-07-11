from healthchain.cda_parser.cdaannotator import (
    SectionId,
    ProblemConcept,
)


def test_find_notes_section(cda_annotator):
    # Test if the notes section is found correctly
    section = cda_annotator._find_notes_section()
    assert section is not None
    assert section.templateId.root == SectionId.NOTE.value


def test_find_problems_section(cda_annotator):
    section = cda_annotator._find_problems_section()
    assert section is not None
    assert section.templateId.root == SectionId.PROBLEM.value


def test_find_medications_section(cda_annotator):
    section = cda_annotator._find_medications_section()
    assert section is not None
    assert section.templateId[0].root == SectionId.MEDICATION.value


def test_find_allergies_section(cda_annotator):
    section = cda_annotator._find_allergies_section()
    assert section is not None
    assert section.templateId[0].root == SectionId.ALLERGY.value


def test_extract_note(cda_annotator):
    # Test if the note is extracted correctly
    note = cda_annotator._extract_note()
    assert note == {"paragraph": "test"}


def test_extract_problems(cda_annotator):
    problems = cda_annotator._extract_problems()

    assert len(problems) == 1
    assert problems[0].code == "38341003"
    assert problems[0].code_system == "2.16.840.1.113883.6.96"
    assert problems[0].code_system_name == "SNOMED CT"


def test_add_to_problem_list(cda_annotator, test_ccd_data):
    # Test if problems are added to the problem list correctly with overwrite=True
    problems = test_ccd_data.problems
    cda_annotator.add_to_problem_list(problems, overwrite=True)
    assert len(cda_annotator.problem_list) == 1
    assert len(cda_annotator._problem_section.entry) == 1

    cda_annotator.add_to_problem_list(problems)
    assert len(cda_annotator.problem_list) == 2
    assert len(cda_annotator._problem_section.entry) == 2


# def test_add_to_allergy_list_overwrite(cda_annotator, test_ccd_data):
#     # Test if allergies are added to the allergy list correctly with overwrite=True
#     allergies = test_ccd_data.allergies
#     cda_annotator.add_to_allergy_list(allergies, overwrite=True)
#     assert len(cda_annotator.allergy_list) == 1

#     cda_annotator.add_to_allergy_list(allergies)
#     assert len(cda_annotator.allergy_list) == 2


# def test_add_to_medication_list_overwrite(cda_annotator, test_ccd_data):
#     # Test if medications are added to the medication list correctly with overwrite=True
#     medications = test_ccd_data.medications
#     cda_annotator.add_to_medication_list(medications, overwrite=True)
#     assert len(cda_annotator.medication_list) == 1

#     cda_annotator.add_to_medication_list(medications)
#     assert len(cda_annotator.medication_list) == 2


def test_export_pretty_print(cda_annotator):
    # Test if the export function returns a valid string with pretty_print=True
    exported_data = cda_annotator.export(pretty_print=True)
    assert isinstance(exported_data, str)
    assert "\t" in exported_data


def test_export_no_pretty_print(cda_annotator):
    # Test if the export function returns a valid string with pretty_print=False
    exported_data = cda_annotator.export(pretty_print=False)
    assert isinstance(exported_data, str)


def test_add_new_problem_entry(cda_annotator):
    # Test if a new problem entry is added correctly
    new_problem = ProblemConcept()
    new_problem.code = "12345678"
    new_problem.code_system = "2.16.840.1.113883.6.96"
    new_problem.code_system_name = "SNOMED CT"
    new_problem.display_name = "Test Problem"
    timestamp = "20220101"
    act_id = "12345678"
    problem_reference_name = "#p12345678name"

    cda_annotator._add_new_problem_entry(
        new_problem=new_problem,
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
        "@code": new_problem.code,
        "@codeSystem": new_problem.code_system,
        "@codeSystemName": new_problem.code_system_name,
        "@displayName": new_problem.display_name,
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
