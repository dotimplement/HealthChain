from healthchain.data_generator.base_generators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)
from healthchain.fhir_resources.base_resources import (
    PeriodModel,
    CodeableConceptModel,
    stringModel,
    CodingModel,
    uriModel,
    codeModel,
    dateTimeModel,
    positiveIntModel,
)
from healthchain.fhir_resources.patient_resources import (
    PatientModel,
    HumanNameModel,
    ContactPointModel,
    AddressModel,
)
from faker import Faker

import random

faker = Faker()


@register_generator
class PeriodGenerator(BaseGenerator):
    @staticmethod
    def generate():
        start = faker.date_time()
        end = faker.date_time_between(start_date=start).isoformat()
        start = start.isoformat()
        return PeriodModel(
            start=dateTimeModel(start),
            end=dateTimeModel(end),
        )


@register_generator
class ContactPointGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return ContactPointModel(
            system=codeModel(
                faker.random_element(
                    elements=("phone", "fax", "email", "pager", "url", "sms", "other")
                )
            ),
            value=stringModel(faker.phone_number()),
            use=codeModel(faker.random_element(elements=("home", "work"))),
            rank=positiveIntModel(random.randint(1, 10)),
            period=generator_registry.get("PeriodGenerator").generate(),
        )


@register_generator
class AddressGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return AddressModel(
            use=codeModel(
                faker.random_element(elements=("home", "work", "temp", "old"))
            ),
            type=codeModel(
                faker.random_element(elements=("postal", "physical", "both"))
            ),
            text=stringModel(faker.address()),
            line=[stringModel(faker.street_address())],
            city=stringModel(faker.city()),
            district=stringModel(faker.state()),
            state=stringModel(faker.state_abbr()),
            postalCode=stringModel(faker.postcode()),
            country=stringModel(faker.country_code()),
            period=generator_registry.get("PeriodGenerator").generate(),
        )


@register_generator
class maritalStatusGenerator(BaseGenerator):
    def generate():
        marital_status_dict = {
            "D": "Divorced",
            "L": "Legally Separated",
            "M": "Married",
        }
        marital_code = faker.random_element(elements=(marital_status_dict.keys()))
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system=uriModel(
                        "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus"
                    ),
                    code=codeModel(marital_code),
                    display=stringModel(marital_status_dict.get(marital_code)),
                )
            ],
            text=stringModel(marital_status_dict.get(marital_code)),
        )


@register_generator
class HumanNameGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return HumanNameModel(
            family=stringModel(faker.last_name()),
            given=[stringModel(faker.first_name())],
            prefix=[stringModel(faker.prefix())],
            suffix=[stringModel(faker.suffix())],
        )


@register_generator
class PatientGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return PatientModel(
            resourceType="Patient",
            id=generator_registry.get("idGenerator").generate(),
            active=generator_registry.get("booleanGenerator").generate(),
            name=[generator_registry.get("HumanNameGenerator").generate()],
            telecom=[
                generator_registry.get("ContactPointGenerator").generate()
                for _ in range(1)
            ],  ## List of length 1 for simplicity
            gender=codeModel(
                faker.random_element(elements=("male", "female", "other", "unknown"))
            ),
            birthDate=generator_registry.get("dateGenerator").generate(),
            address=[
                generator_registry.get("AddressGenerator").generate() for _ in range(1)
            ],  ## List of length 1 for simplicity
            maritalStatus=generator_registry.get("maritalStatusGenerator").generate(),
        )
