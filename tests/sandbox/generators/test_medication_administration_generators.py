from healthchain.sandbox.generators.medicationadministrationgenerators import (
    MedicationAdministrationDosageGenerator,
    MedicationAdministrationGenerator,
)
from healthchain.sandbox.generators.value_sets.medicationcodes import (
    MedicationRequestMedication,
)


def test_MedicationAdministrationDosageGenerator():
    result = MedicationAdministrationDosageGenerator.generate()
    assert result.text is not None


def test_MedicationAdministrationGenerator():
    value_set = [x.code for x in MedicationRequestMedication().value_set]
    result = MedicationAdministrationGenerator.generate("Patient/123", "Encounter/123")
    assert result.id is not None
    assert result.status is not None
    assert result.medication is not None
    assert result.medication.concept.coding[0].code in value_set
