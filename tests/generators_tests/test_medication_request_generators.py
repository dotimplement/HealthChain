from healthchain.data_generators.medicationrequestgenerators import (
    MedicationRequestGenerator,
    MedicationRequestContainedGenerator,
)


def test_MedicationGenerator():
    generator = MedicationRequestContainedGenerator()
    medication = generator.generate()
    assert medication is not None


def test_MedicationRequestGenerator():
    generator = MedicationRequestGenerator()
    medication_request = generator.generate()
    assert medication_request is not None
    assert medication_request.resourceType == "MedicationRequest"
    assert medication_request.id_field is not None
