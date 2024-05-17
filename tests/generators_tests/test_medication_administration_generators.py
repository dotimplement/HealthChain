from healthchain.data_generator.medication_administration_generators import (
    MedicationAdministrationDosageGenerator,
    MedicationAdministrationGenerator,
)


def test_MedicationAdministrationDosageGenerator():
    result = MedicationAdministrationDosageGenerator.generate()
    assert result.text_field is not None


def test_MedicationAdministrationGenerator():
    result = MedicationAdministrationGenerator.generate("Patient/123", "Encounter/123")
    assert result.id_field is not None
    assert result.status_field is not None
    assert result.medication_field is not None
