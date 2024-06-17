from typing import Optional
from faker import Faker

from healthchain.data_generators.basegenerators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)
from healthchain.fhir_resources.primitives import (
    booleanModel,
    stringModel,
    uriModel,
    codeModel,
)
from healthchain.fhir_resources.generalpurpose import (
    CodeableConcept,
    Coding,
)
from healthchain.fhir_resources.practitioner import (
    Practitioner,
    PractitionerQualification,
    PractitionerCommunication,
)


faker = Faker()


@register_generator
class QualificationGenerator(BaseGenerator):
    # TODO: Update with realistic qualifications
    qualification_dict = {
        "12345": "Qualification 1",
        "67890": "Qualification 2",
        "54321": "Qualification 3",
        "09876": "Qualification 4",
        "65432": "Qualification 5",
    }

    @staticmethod
    def generate():
        random_qual = faker.random_element(
            elements=QualificationGenerator.qualification_dict.keys()
        )
        return CodeableConcept(
            coding=[
                Coding(
                    system=uriModel("http://example.org"),
                    code=codeModel(random_qual),
                    display=stringModel(
                        QualificationGenerator.qualification_dict.get(random_qual)
                    ),
                )
            ],
            text=stringModel(
                QualificationGenerator.qualification_dict.get(random_qual)
            ),
        )


@register_generator
class Practitioner_QualificationGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return PractitionerQualification(
            id=stringModel(faker.uuid4()),
            code=generator_registry.get("QualificationGenerator").generate(),
            # TODO: Modify period generator to have flexibility to set to present date
            period=generator_registry.get("PeriodGenerator").generate(),
            # issuer=generator_registry.get('ReferenceGenerator').generate(),
        )


@register_generator
class LanguageGenerator:
    @staticmethod
    def generate():
        language_value_dict = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ru": "Russian",
            "ar": "Arabic",
        }
        language = faker.random_element(elements=language_value_dict.keys())
        return CodeableConcept(
            coding=[
                Coding(
                    system=uriModel("http://terminology.hl7.org/CodeSystem/languages"),
                    code=codeModel(language),
                    display=stringModel(language_value_dict.get(language)),
                )
            ],
            text=stringModel(language_value_dict.get(language)),
        )


@register_generator
class Practitioner_CommunicationGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return PractitionerCommunication(
            id=stringModel(faker.uuid4()),
            language=generator_registry.get("LanguageGenerator").generate(),
            preferred=booleanModel("true"),
        )


@register_generator
class PractitionerGenerator(BaseGenerator):
    @staticmethod
    def generate(constraints: Optional[list] = None):
        return Practitioner(
            id=stringModel(faker.uuid4()),
            active=booleanModel("true"),
            name=[generator_registry.get("HumanNameGenerator").generate()],
            telecom=[generator_registry.get("ContactPointGenerator").generate()],
            gender=codeModel(
                faker.random_element(elements=("male", "female", "other", "unknown"))
            ),
            address=[generator_registry.get("AddressGenerator").generate()],
            qualification=[
                generator_registry.get("Practitioner_QualificationGenerator").generate()
            ],
            communication=[
                generator_registry.get("Practitioner_CommunicationGenerator").generate()
            ],
        )
