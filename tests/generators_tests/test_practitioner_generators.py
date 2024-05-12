from healthchain.data_generator.practitioner_generator import PractitionerGenerator, Practitioner_QualificationGenerator, Practitioner_CommunicationGenerator

def test_practitioner_data_generator():
    # Create an instance of the PractitionerDataGenerator
    generator = PractitionerGenerator()

    # Generate practitioner data
    practitioner_data = generator.generate()

    # Assert that the practitioner data is not empty
    assert practitioner_data is not None

    # Assert that the practitioner data has the expected pydantic fields
    assert practitioner_data.resourceType == "Practitioner"
    assert practitioner_data.id_field is not None
    assert practitioner_data.active_field is not None
    assert practitioner_data.name_field is not None
    assert practitioner_data.qualification_field is not None
    assert practitioner_data.communication_field is not None

    # Assert that the qualification data has the expected pydantic fields
    qualification_data = practitioner_data.qualification_field[0]
    assert qualification_data.id_field is not None
    assert qualification_data.code_field is not None
    assert qualification_data.period_field is not None

    # Assert that the communication data has the expected pydantic fields
    communication_data = practitioner_data.communication_field[0]
    assert communication_data.id_field is not None
    assert communication_data.language_field is not None
    assert communication_data.preferred_field is not None


def test_practitioner_qualification_generator():
    # Create an instance of the PractitionerQualificationGenerator
    generator = Practitioner_QualificationGenerator()

    # Generate a practitioner qualification
    qualification = generator.generate()

    # Assert that the qualification is not empty
    assert qualification is not None

    # Assert that the qualification has the expected pydantic fields
    assert qualification.id_field is not None
    assert qualification.code_field is not None
    assert qualification.period_field is not None


def test_practitioner_communication_generator():
    # Create an instance of the PractitionerCommunicationGenerator
    generator = Practitioner_CommunicationGenerator()

    # Generate a practitioner communication
    communication = generator.generate()

    # Assert that the communication is not empty
    assert communication is not None

    # Assert that the communication has the expected pydantic fields
    assert communication.id_field is not None
    assert communication.language_field is not None
    assert communication.preferred_field is not None