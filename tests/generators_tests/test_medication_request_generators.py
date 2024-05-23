from healthchain.data_generator.medication_request_generators import (
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
    assert medication_request.resourceType_field == "MedicationRequest"
    assert medication_request.id_field is not None
