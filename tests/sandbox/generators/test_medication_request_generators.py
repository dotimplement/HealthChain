from healthchain.sandbox.generators.medicationrequestgenerators import (
    MedicationRequestGenerator,
    MedicationRequestContainedGenerator,
)
from healthchain.sandbox.generators.value_sets.medicationcodes import (
    MedicationRequestMedication,
)


def test_MedicationGenerator():
    generator = MedicationRequestContainedGenerator()
    medication = generator.generate()
    value_set = [x.code for x in MedicationRequestMedication().value_set]
    assert medication is not None
    assert medication.coding[0].code in value_set


def test_MedicationRequestGenerator():
    generator = MedicationRequestGenerator()
    medication_request = generator.generate()
    value_set = [x.code for x in MedicationRequestMedication().value_set]
    assert medication_request is not None
    assert medication_request.id is not None
    assert medication_request.medication.concept.coding[0].code in value_set
    assert medication_request.intent is not None
