from healthchain.data_generators.medicationrequestgenerators import (
    MedicationRequestGenerator,
    MedicationRequestContainedGenerator,
)
from healthchain.data_generators.value_sets.medicationcodes import (
    MedicationRequestMedication,
)


def test_MedicationGenerator():
    generator = MedicationRequestContainedGenerator()
    medication = generator.generate()
    assert medication is not None


def test_MedicationRequestGenerator():
    generator = MedicationRequestGenerator()
    medication_request = generator.generate()
    value_set = [x.code for x in MedicationRequestMedication().value_set]
    assert medication_request is not None
    assert medication_request.id is not None
    assert medication_request.contained[0].code.coding[0].code in value_set
