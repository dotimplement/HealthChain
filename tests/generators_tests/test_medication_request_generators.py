from healthchain.data_generator.medication_request_generators import (
    MedicationRequestGenerator,
    MedicationGenerator,
)


def test_MedicationGenerator():
    generator = MedicationGenerator()
    medication = generator.generate()
    assert medication is not None


def test_MedicationRequestGenerator():
    generator = MedicationRequestGenerator()
    medication_request = generator.generate("Patient/123", "Encounter/123")
    assert medication_request is not None
    assert medication_request.resourceType_field == "MedicationRequest"
    assert medication_request.id_field is not None
