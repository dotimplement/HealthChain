from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Literal
from datetime import datetime
from faker import Faker
from pandas import Period

fake = Faker()

class BaseLiterals:
    gender = Literal['male', 'female', 'other', 'unknown']


class Coding(BaseModel):
    system: str = Field(default=None, alias='system', description='Identity of the terminology system')
    version: str = Field(default=None, alias='version', description='Version of the system - if relevant')
    code: str = Field(default=None, alias='code', description='Symbol in syntax defined by the system')
    display: str = Field(default=None, alias='display', description='Representation defined by the system')
    userSelected: bool = Field(default=None, alias='userSelected', description='If this coding was chosen directly by the user')


class CodeableConcept(BaseModel):
    coding: List[Coding] = Field(default=None, alias='coding', description='Code defined by a terminology system')
    text: str = Field(default=None, alias='text', description='Plain text representation of the concept')


class Reference(BaseModel):
    reference: str = Field(default=None, alias='reference', description='Relative, internal or absolute URL reference')
    type: str = Field(default=None, alias='type', description='Type the reference refers to (e.g. "Patient")')
    identifier: "Identifier" = Field(default=None, alias='identifier', description='Logical reference, when literal reference is not known')


class Identifier(BaseModel):
    use: str = Field(default=None, alias='use', description='usual | official | temp | secondary | old (If known)')
    type: CodeableConcept = Field(default=None, alias='type', description='Description of identifier')
    system: str = Field(default=None, alias='system', description='The namespace for the identifier value')
    value: str = Field(default=None, alias='value', description='The value that is unique')
    period: Period = Field(default=None, alias='period', description='Time period when the identifier was valid for use')
    assigner: "Reference" = Field(default=None, alias='assigner', description='Organization that issued id (may be just text)')


Reference.update_forward_refs()
Identifier.update_forward_refs()

class HumanName(BaseModel):
    use: str = Field(default=None, alias='use', description='usual | official | temp | nickname | anonymous | old | maiden')
    text: str = Field(default=None, alias='text', description='Text representation of the full name')
    family: List[str] = Field(default=None, alias='family', description='Family name (often called 'Surname'')
    given: List[str] = Field(default=None, alias='given', description='Given names (not always 'first'). Includes middle names')
    prefix: List[str] = Field(default=None, alias='prefix', description='Parts that come before the name')
    suffix: List[str] = Field(default=None, alias='suffix', description='Parts that come after the name')
    period: Period = Field(default=None, alias='period', description='Time period when name was/is in use')


class ContactPoint(BaseModel):
    system: str = Field(default=None, alias='system', description='phone | fax | email | pager | url | sms | other')
    value: str = Field(default=None, alias='value', description='The actual contact point details')
    use: str = Field(default=None, alias='use', description='home | work | temp | old | mobile - purpose of this contact point')
    rank: int = Field(default=None, alias='rank', description='Specify preferred order of use (1 = highest)')
    period: Period = Field(default=None, alias='period', description='Time period when the contact point was/is in use')


class Address(BaseModel):
    use: str = Field(default=None, alias='use', description='home | work | temp | old - purpose of this address')
    type: str = Field(default=None, alias='type', description='postal | physical | both')
    text: str = Field(default=None, alias='text', description='Text representation of the address')
    line: List[str] = Field(default=None, alias='line', description='Street name, number, direction & P.O. Box etc')
    city: str = Field(default=None, alias='city', description='Name of city, town etc.')
    district: str = Field(default=None, alias='district', description='District name (aka county)')
    state: str = Field(default=None, alias='state', description='Sub-unit of country (abbreviations ok)')
    postalCode: str = Field(default=None, alias='postalCode', description='Postal code for area')
    country: str = Field(default=None, alias='country', description='Country (can be ISO 3166 3 letter code)')


class Attachment(BaseModel):
    contentType: str = Field(default=None, alias='contentType', description='Mime type of the content, with charset etc.')
    language: str = Field(default=None, alias='language', description='Human language of the content (BCP-47)')
    data: str = Field(default=None, alias='data', description='Data inline, base64ed')
    url: str = Field(default=None, alias='url', description='Uri where the data can be found')
    size: int = Field(default=None, alias='size', description='Number of bytes of content (if url provided)')
    hash: str = Field(default=None, alias='hash', description='Hash of the data (sha-1, base64ed)')
    title: str = Field(default=None, alias='title', description='Label to display in place of the data')


class PatientContact(BaseModel):
    relationship: List[CodeableConcept] = Field(default=None, alias='relationship', description='The kind of relationship')
    name: HumanName = Field(default=None, alias='name', description='A name associated with the contact person')
    telecom: List[ContactPoint] = Field(default=None, alias='telecom', description='A contact detail for the person')
    address: Address = Field(default=None, alias='address', description='Address for the contact person')


class PatientCommunication(BaseModel):
    language: CodeableConcept = Field(default=None, alias='language', description='The language which can be used for communication')
    preferred: bool = Field(default=None, alias='preferred', description='Language preference indicator')


class PatientLink(BaseModel):
    other: Reference = Field(default=None, alias='other', description='The other patient resource that the link refers to')
    type: str = Field(default=None, alias='type', description='replaced-by | replaces | refer | seealso - type of link')


class Patient(BaseModel):
    resource_type: str = Field("Patient", const=True)
    identifier: List[Identifier] = Field(default=None, alias="identifier", description="An identifier for this patient")
    active: bool = Field(default=None, alias="active", description="Whether this patient's record is in active use")
    name: List[HumanName] = Field(default=None, alias="name", description="A name associated with the patient")
    telecom: List[ContactPoint] = Field(default=None, alias="telecom", description="A contact detail for the individual")
    gender: BaseLiterals.gender = Field(default=None, alias='gender', description='male | female | other | unknown')
    birthDate: datetime = Field(default=None, alias='birthDate', description='The date of birth for the individual')
    deceased: bool | datetime = Field(default=None, alias='deceased', description='Indicates if the individual is deceased or not')
    address: List[Address] = Field(default=None, alias='address', description='Addresses for the individual')
    maritalStatus: CodeableConcept = Field(default=None, alias='maritalStatus', description='Marital (civil) status of a patient')
    multipleBirth: bool | int = Field(default=None, alias='multipleBirth', description='Whether patient is part of a multiple birth')
    photo: List[Attachment] = Field(default=None, alias='photo', description='Image of the patient')
    contact: List[PatientContact] = Field(default=None, alias='contact', description='A contact party (e.g. guardian, partner, friend) for the patient')
    communication: List[PatientCommunication] = Field(default=None, alias='communication', description='A language which may be used to communicate with the patient about his or her health')
    generalPractitioner: List[Reference] = Field(default=None, alias='generalPractitioner', description='Patient\'s nominated care provider')
    managingOrganization: Reference = Field(default=None, alias='managingOrganization', description='Organization that is the custodian of the patient record')
    link: List[PatientLink] = Field(default=None, alias='link', description='Link to another patient resource that concerns the same actual person')





                                                 


class Address(BaseModel):
    city: str = Field(default_factory=lambda: fake.city())
    country: str = Field(default_factory=lambda: fake.country())
    
    # Placeholder for actual data retrieval logic
    @validator('city', pre=True, always=True)
    def adjust_city_to_country(cls, v, values, **kwargs):
        country = values.get('country')
        # Here you would adjust 'v' to be a city from 'country'
        # This is a placeholder logic.
        return v


class HumanName(BaseModel):
    family: str = Field(default_factory=lambda: fake.last_name())
    given: List[str] = Field(default_factory=lambda: [fake.first_name()])
    prefix: List[str] = Field(default_factory=lambda: [fake.prefix()])
    suffix: List[str] = Field(default_factory=lambda: [fake.suffix()])



# class ContactPoint(BaseModel):
#     system: str = Field(default_factory=lambda: fake.random_element(elements=("phone", "email")))
#     value: str = Field(default_factory=lambda system=system: fake.phone_number() if system == "phone" else fake.email())
#     use: str = Field(default_factory=lambda: fake.random_element(elements=("home", "work", "temp")))
#     rank: int = Field(default_factory=lambda: fake.random_int(min=1, max=3))

# class Address(BaseModel):
#     use: str = Field(default_factory=lambda: fake.random_element(elements=("home", "work", "temp")))
#     type: str = Field(default_factory=lambda: fake.random_element(elements=("postal", "physical")))
#     text: str = Field(default_factory=lambda: fake.address())
#     line: List[str] = Field(default_factory=lambda: [fake.street_address()])
#     city: str = Field(default_factory=lambda: fake.city())
#     district: str = Field(default_factory=lambda: fake.state())
#     state: str = Field(default_factory=lambda: fake.state())
#     postalCode: str = Field(default_factory=lambda: fake.zipcode())
#     country: str = Field(default_factory=lambda: fake.country())

# class Patient(BaseModel):
#     id: str = Field(default_factory=lambda: fake.uuid4())
#     active: bool = Field(default_factory=lambda: fake.boolean())
#     name: List[HumanName] = Field(default_factory=lambda: [HumanName()])
#     telecom: List[ContactPoint] = Field(default_factory=lambda: [ContactPoint()])
#     gender: str = Field(default_factory=lambda: fake.random_element(elements=("male", "female", "other", "unknown")))
#     birthDate: datetime = Field(default_factory=lambda: fake.date_of_birth(minimum_age=0, maximum_age=100))
#     address: List[Address] = Field(default_factory=lambda: [Address()])

# class Practitioner(BaseModel):
#     id: str = Field(default_factory=lambda: fake.uuid4())
#     active: bool = Field(default_factory=lambda: fake.boolean())
#     name: List[HumanName] = Field(default_factory=lambda: [HumanName()])
#     telecom: List[ContactPoint] = Field(default_factory=lambda: [ContactPoint()])
#     address: List[Address] = Field(default_factory=lambda: [Address()])
#     gender: str = Field(default_factory=lambda: fake.random_element(elements=("male", "female", "other", "unknown")))
#     birthDate: datetime = Field(default_factory=lambda: fake.date_of_birth(minimum_age=25, maximum_age=70))

# class Observation(BaseModel):
#     id: str = Field(default_factory=lambda: fake.uuid4())
#     status: str = Field(default_factory=lambda: fake.random_element(elements=("registered", "preliminary", "final")))
#     effectiveDateTime: datetime = Field(default_factory=lambda: fake.past_date())
#     issued: datetime = Field(default_factory=lambda: fake.date_time_this_month())

