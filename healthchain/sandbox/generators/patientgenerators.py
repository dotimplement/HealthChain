from typing import Optional
from faker import Faker

from healthchain.sandbox.generators.basegenerators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)

from datetime import datetime

from fhir.resources.humanname import HumanName
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.address import Address
from fhir.resources.period import Period
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.patient import Patient


faker = Faker()


# TODO: Move to common gens
@register_generator
class PeriodGenerator(BaseGenerator):
    @staticmethod
    def generate():
        # Use date_between instead of date() for more control
        start = faker.date_between(
            start_date="-30y",  # You can adjust this range
            end_date="today",
        )
        end = faker.date_between_dates(date_start=start, date_end=datetime.now())
        return Period(
            start=start,
            end=end,
        )


@register_generator
class ContactPointGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return ContactPoint(
            system=faker.random_element(elements=("phone", "fax")),
            value=faker.phone_number(),
            use=faker.random_element(elements=("home", "work")),
            rank=1,
            period=generator_registry.get("PeriodGenerator").generate(),
        )


@register_generator
class AddressGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return Address(
            use=faker.random_element(elements=("home", "work", "temp", "old")),
            type=faker.random_element(elements=("postal", "physical", "both")),
            text=faker.address(),
            line=[faker.street_address()],
            city=faker.city(),
            district=faker.state(),
            state=faker.state_abbr(),
            postalCode=faker.postcode(),
            country=faker.country_code(),
            period=generator_registry.get("PeriodGenerator").generate(),
        )


@register_generator
class MaritalStatusGenerator(BaseGenerator):
    @staticmethod
    def generate():
        marital_status_dict = {
            "D": "Divorced",
            "L": "Legally Separated",
            "M": "Married",
        }
        marital_code = faker.random_element(elements=(marital_status_dict.keys()))
        return CodeableConcept(
            coding=[
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                    code=marital_code,
                    display=marital_status_dict.get(marital_code),
                )
            ],
            text=marital_status_dict.get(marital_code),
        )


@register_generator
class HumanNameGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return HumanName(
            family=faker.last_name(),
            given=[faker.first_name()],
            prefix=[faker.prefix()],
            suffix=[faker.suffix()],
        )


@register_generator
class PatientGenerator(BaseGenerator):
    @staticmethod
    def generate(
        constraints: Optional[list] = None,
        random_seed: Optional[int] = None,
    ) -> Patient:
        Faker.seed(random_seed)
        return Patient(
            id=generator_registry.get("IdGenerator").generate(),
            active=generator_registry.get("BooleanGenerator").generate(),
            name=[generator_registry.get("HumanNameGenerator").generate()],
            telecom=[generator_registry.get("ContactPointGenerator").generate()],
            gender=faker.random_element(
                elements=("male", "female", "other", "unknown")
            ),
            birthDate=generator_registry.get("DateGenerator").generate(),
            address=[
                generator_registry.get("AddressGenerator").generate() for _ in range(1)
            ],  ## List of length 1 for simplicity
            maritalStatus=generator_registry.get("MaritalStatusGenerator").generate(),
        )
