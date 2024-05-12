from healthchain.data_generator.base_generators import BaseGenerator, generator_registry, register_generator
from healthchain.fhir_resources.base_resources import PeriodModel, booleanModel, CodeableConceptModel, stringModel, CodingModel, uriModel, codeModel
from healthchain.fhir_resources.practitioner_resources import PractitionerModel, Practitioner_QualificationModel, Practitioner_CommunicationModel
from faker import Faker


import random

faker = Faker()


@register_generator
class QualificationGenerator(BaseGenerator):
    # TODO: Update with realistic qualifications
    qualification_dict = {
        '12345': 'Qualification 1',
        '67890': 'Qualification 2',
        '54321': 'Qualification 3',
        '09876': 'Qualification 4',
        '65432': 'Qualification 5',
    }
    @staticmethod
    def generate():
        random_qual = faker.random_element(elements=QualificationGenerator.qualification_dict.keys())
        return CodeableConceptModel(
            coding=[CodingModel(
                system=uriModel("http://example.org"),
                code=codeModel(random_qual),
                display=stringModel(QualificationGenerator.qualification_dict.get(random_qual))
            )],
            text=stringModel(QualificationGenerator.qualification_dict.get(random_qual))
        )

@register_generator
class Practitioner_QualificationGenerator(BaseGenerator):
    # TODO: Refactor the value set to live with the resources



    @staticmethod
    def generate():
        return Practitioner_QualificationModel(
            id=stringModel(faker.uuid4()),
            code=generator_registry.get('QualificationGenerator').generate(),
            # TODO: Modify period generator to have flexibility to set to present date
            period=generator_registry.get('PeriodGenerator').generate(),
            # issuer=generator_registry.get('ReferenceGenerator').generate(),
        )



@register_generator
class LanguageGenerator():
    language_value_dict = {'en': 'English',
                           'es': 'Spanish',
                           'fr': 'French',
                           'de': 'German',
                           'it': 'Italian',
                           'ja': 'Japanese',
                           'ko': 'Korean',
                           'zh': 'Chinese',
                           'ru': 'Russian',
                           'ar': 'Arabic'}
    @staticmethod
    def generate():
        language = faker.random_element(elements=LanguageGenerator.language_value_dict.keys())
        return CodeableConceptModel(
            coding=[CodingModel(
                system=uriModel("http://terminology.hl7.org/CodeSystem/languages"),
                code=codeModel(language),
                display=stringModel(LanguageGenerator.language_value_dict.get(language))
                )],
            text=stringModel(LanguageGenerator.language_value_dict.get(language))
        )

@register_generator
class Practitioner_CommunicationGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return Practitioner_CommunicationModel(
            id=stringModel(faker.uuid4()),
            language=generator_registry.get('LanguageGenerator').generate(),
            preferred=booleanModel(random.choice(['true', 'false'])),
        )
    

@register_generator
class PractitionerGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return PractitionerModel(
            id=stringModel(faker.uuid4()),
            active=booleanModel(random.choice(['true', 'false'])),
            name=[generator_registry.get('HumanNameGenerator').generate()],
            telecom=[generator_registry.get('ContactPointGenerator').generate()],
            gender=codeModel(faker.random_element(elements=('male', 'female', 'other', 'unknown'))),
            address=[generator_registry.get('AddressGenerator').generate()],
            qualification=[generator_registry.get('Practitioner_QualificationGenerator').generate()],
            communication=[generator_registry.get('Practitioner_CommunicationGenerator').generate()],

        )