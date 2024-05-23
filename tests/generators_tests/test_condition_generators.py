from healthchain.data_generator.condition_generators import (
    ClinicalStatusGenerator,
    VerificationStatusGenerator,
    CategoryGenerator,
    ConditionGenerator,
)


def test_ClinicalStatusGenerator():
    clinical_status = ClinicalStatusGenerator.generate()
    assert (
        clinical_status.coding_field[0].system_field
        == "http://terminology.hl7.org/CodeSystem/condition-clinical"
    )
    assert clinical_status.coding_field[0].code_field in (
        "active",
        "recurrence",
        "inactive",
        "resolved",
    )


def test_VerificationStatusGenerator():
    verification_status = VerificationStatusGenerator.generate()
    assert (
        verification_status.coding_field[0].system_field
        == "http://terminology.hl7.org/CodeSystem/condition-ver-status"
    )
    assert verification_status.coding_field[0].code_field in (
        "provisional",
        "confirmed",
    )


def test_CategoryGenerator():
    category = CategoryGenerator.generate()
    assert category.coding_field[0].system_field == "http://snomed.info/sct"
    assert category.coding_field[0].code_field in ("55607006", "404684003")


def test_ConditionGenerator():
    condition_model = ConditionGenerator.generate("Patient/456", "Encounter/789")
    assert condition_model.resourceType == "Condition"
    assert condition_model.subject_field.reference_field == "Patient/456"
    assert condition_model.encounter_field.reference_field == "Encounter/789"
    assert condition_model.id_field is not None
    assert condition_model.subject_field is not None
    assert condition_model.encounter_field is not None
    assert condition_model.code_field is not None
