from healthchain.data_generators.medicationadministrationgenerators import (
    MedicationAdministrationDosageGenerator,
    MedicationAdministrationGenerator,
)


def test_MedicationAdministrationDosageGenerator():
    result = MedicationAdministrationDosageGenerator.generate()
    assert result.text is not None


def test_MedicationAdministrationGenerator():
    result = MedicationAdministrationGenerator.generate("Patient/123", "Encounter/123")
    assert result.id is not None
    assert result.status is not None
    assert result.medication is not None
