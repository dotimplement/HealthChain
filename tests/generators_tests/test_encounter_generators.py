from healthchain.data_generator.encounter_generator import (
    ClassGenerator,
    EncounterTypeGenerator,
    EncounterGenerator,
)


def test_ClassGenerator():
    patient_class = ClassGenerator.generate()
    assert (
        patient_class.coding_field[0].system_field
        == "http://terminology.hl7.org/CodeSystem/v3-ActCode"
    )
    assert patient_class.coding_field[0].code_field in ("IMP", "AMB")
    assert patient_class.coding_field[0].display_field in ("inpatient", "ambulatory")


def test_EncounterTypeGenerator():
    encounter_type = EncounterTypeGenerator.generate()
    assert encounter_type.coding_field[0].system_field == "http://snomed.info/sct"
    assert encounter_type.coding_field[0].display_field in ("consultation", "emergency")


def test_EncounterModel():
    encounter = EncounterGenerator.generate(patient_reference="Patient/123")

    assert encounter.resourceType == "Encounter"
    assert encounter.id_field is not None
    assert encounter.text_field is not None
    assert encounter.status_field in (
        "planned",
        "in-progress",
        "on-hold",
        "discharged",
        "cancelled",
    )
    assert encounter.class_field is not None
    assert encounter.type_field is not None
    assert encounter.subject_field is not None
    assert encounter.subject_field.reference_field == "Patient/123"
    assert encounter.subject_field.display_field == "Patient/123"
