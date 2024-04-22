
from abc import ABC, abstractmethod
from pydantic import BaseModel
from faker import Faker
from src.data_generator.fhir_data import Patient, HumanName
import random

class AbstractDataGenerator(ABC):
    @abstractmethod
    def generate(self) -> BaseModel:
        """Generate an instance of a Pydantic model."""
        pass


faker = Faker()

class HumanNameGenerator(AbstractDataGenerator):
    def generate(self) -> HumanName:
        return HumanName(
            family=faker.last_name(),
            given=[faker.first_name()],
            prefix=[faker.prefix()],
            suffix=[faker.suffix()]  ## We probably don't want to generate suffixes every time
        )

class PatientGenerator(AbstractDataGenerator):
    def generate(self) -> Patient:
        return Patient(
            id=faker.uuid4(),
            active=faker.boolean(),
            name=[HumanNameGenerator().generate()],
            telecom=[{
                "system": faker.random_element(elements=("phone", "email")),
                "value": faker.phone_number() if system == "phone" else faker.email(),
                "use": faker.random_element(elements=("home", "work", "temp")),
                "rank": faker.random_int(min=1, max=3)
            }],
            gender=faker.random_element(elements=("

