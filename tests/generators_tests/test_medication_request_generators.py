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
    assert medication_request.resourceType == "MedicationRequest"
    assert medication_request.id_field is not None
    assert (
        medication_request.contained_field[0].code_field.coding_field[0].code_field
        in value_set
    )
