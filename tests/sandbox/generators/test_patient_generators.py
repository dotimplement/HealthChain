from healthchain.sandbox.generators.patientgenerators import (
    PatientGenerator,
    HumanNameGenerator,
)


def test_human_name_generator():
    # Create an instance of the HumanNameGenerator
    generator = HumanNameGenerator()

    # Generate a human name
    human_name = generator.generate()

    assert human_name is not None


def test_patient_data_generator():
    # Create an instance of the PatientDataGenerator
    generator = PatientGenerator()

    # Generate patient data
    patient_data = generator.generate()

    # Assert that the patient data is not empty
    assert patient_data is not None

    # Assert that the patient data has the expected pydantic fields
    assert patient_data.id is not None
    assert patient_data.active is not None
