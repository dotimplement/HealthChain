from healthchain.sandbox.generators.conditiongenerators import (
    ClinicalStatusGenerator,
    VerificationStatusGenerator,
    CategoryGenerator,
    ConditionGenerator,
)
from healthchain.sandbox.generators.value_sets.conditioncodes import (
    ConditionCodeSimple,
    ConditionCodeComplex,
)


def test_ClinicalStatusGenerator():
    clinical_status = ClinicalStatusGenerator.generate()
    assert (
        clinical_status.coding[0].system
        == "http://terminology.hl7.org/CodeSystem/condition-clinical"
    )
    assert clinical_status.coding[0].code in (
        "active",
        "recurrence",
        "inactive",
        "resolved",
    )


def test_VerificationStatusGenerator():
    verification_status = VerificationStatusGenerator.generate()
    assert (
        verification_status.coding[0].system
        == "http://terminology.hl7.org/CodeSystem/condition-ver-status"
    )
    assert verification_status.coding[0].code in (
        "provisional",
        "confirmed",
    )


def test_CategoryGenerator():
    category = CategoryGenerator.generate()
    assert category.coding[0].system == "http://snomed.info/sct"
    assert category.coding[0].code in ("55607006", "404684003")


def test_ConditionGenerator():
    condition_model = ConditionGenerator.generate("Patient/456", "Encounter/789")
    value_set = [x.code for x in ConditionCodeSimple().value_set]
    value_set.extend([x.code for x in ConditionCodeComplex().value_set])
    assert condition_model.subject.reference == "Patient/456"
    assert condition_model.encounter.reference == "Encounter/789"
    assert condition_model.id is not None
    assert condition_model.subject is not None
    assert condition_model.encounter is not None
    assert condition_model.code is not None
    assert condition_model.code.coding[0].code in value_set
