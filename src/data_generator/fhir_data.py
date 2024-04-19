from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any
from datetime import datetime
from faker import Faker

fake = Faker()

class HumanName(BaseModel):
    family: str = Field(default_factory=lambda: fake.last_name())
    given: List[str] = Field(default_factory=lambda: [fake.first_name()])
    prefix: List[str] = Field(default_factory=lambda: [fake.prefix()])
    suffix: List[str] = Field(default_factory=lambda: [fake.suffix()])

class ContactPoint(BaseModel):
    system: str = Field(default_factory=lambda: fake.random_element(elements=("phone", "email")))
    value: str = Field(default_factory=lambda system=system: fake.phone_number() if system == "phone" else fake.email())
    use: str = Field(default_factory=lambda: fake.random_element(elements=("home", "work", "temp")))
    rank: int = Field(default_factory=lambda: fake.random_int(min=1, max=3))

class Address(BaseModel):
    use: str = Field(default_factory=lambda: fake.random_element(elements=("home", "work", "temp")))
    type: str = Field(default_factory=lambda: fake.random_element(elements=("postal", "physical")))
    text: str = Field(default_factory=lambda: fake.address())
    line: List[str] = Field(default_factory=lambda: [fake.street_address()])
    city: str = Field(default_factory=lambda: fake.city())
    district: str = Field(default_factory=lambda: fake.state())
    state: str = Field(default_factory=lambda: fake.state())
    postalCode: str = Field(default_factory=lambda: fake.zipcode())
    country: str = Field(default_factory=lambda: fake.country())

class Patient(BaseModel):
    id: str = Field(default_factory=lambda: fake.uuid4())
    active: bool = Field(default_factory=lambda: fake.boolean())
    name: List[HumanName] = Field(default_factory=lambda: [HumanName()])
    telecom: List[ContactPoint] = Field(default_factory=lambda: [ContactPoint()])
    gender: str = Field(default_factory=lambda: fake.random_element(elements=("male", "female", "other", "unknown")))
    birthDate: datetime = Field(default_factory=lambda: fake.date_of_birth(minimum_age=0, maximum_age=100))
    address: List[Address] = Field(default_factory=lambda: [Address()])

class Practitioner(BaseModel):
    id: str = Field(default_factory=lambda: fake.uuid4())
    active: bool = Field(default_factory=lambda: fake.boolean())
    name: List[HumanName] = Field(default_factory=lambda: [HumanName()])
    telecom: List[ContactPoint] = Field(default_factory=lambda: [ContactPoint()])
    address: List[Address] = Field(default_factory=lambda: [Address()])
    gender: str = Field(default_factory=lambda: fake.random_element(elements=("male", "female", "other", "unknown")))
    birthDate: datetime = Field(default_factory=lambda: fake.date_of_birth(minimum_age=25, maximum_age=70))

class Observation(BaseModel):
    id: str = Field(default_factory=lambda: fake.uuid4())
    status: str = Field(default_factory=lambda: fake.random_element(elements=("registered", "preliminary", "final")))
    effectiveDateTime: datetime = Field(default_factory=lambda: fake.past_date())
    issued: datetime = Field(default_factory=lambda: fake.date_time_this_month())

# Example instantiation
patient = Patient()
print(patient)
