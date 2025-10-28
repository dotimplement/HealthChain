from healthchain.sandbox.generators.encountergenerators import (
    ClassGenerator,
    EncounterTypeGenerator,
    EncounterGenerator,
)


def test_ClassGenerator():
    patient_class = ClassGenerator.generate()
    assert (
        patient_class.coding[0].system
        == "http://terminology.hl7.org/CodeSystem/v3-ActCode"
    )
    assert patient_class.coding[0].code in ("IMP", "AMB")
    assert patient_class.coding[0].display in ("inpatient", "ambulatory")


def test_EncounterTypeGenerator():
    encounter_type = EncounterTypeGenerator.generate()
    assert encounter_type.coding[0].system == "http://snomed.info/sct"
    assert encounter_type.coding[0].display in ("consultation", "emergency")


def test_EncounterModel():
    encounter = EncounterGenerator.generate()

    assert encounter.id is not None
    assert encounter.status in (
        "planned",
        "in-progress",
        "on-hold",
        "discharged",
        "cancelled",
    )
    assert encounter.subject.reference == "Patient/123"
    assert encounter.subject.display == "Patient/123"
