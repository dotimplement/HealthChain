import pytest
from healthchain.fhir_resources.patient_resources import PatientModel, HumanNameModel, ContactPointModel, AddressModel

def test_PatientModel():
    data = {
        "resourceType": "Patient",
        "name": [
            {
                "family": "Doe",
                "given": ["John"],
                "prefix": ["Mr."]
            }
        ],
        "birthDate": "1980-01-01",
        "gender": "Male"
    }
    patient = PatientModel(**data)
    patient = patient.model_dump(by_alias=True)
    assert patient['resourceType'] == "Patient"
    assert patient['name'][0]['given'] == ["John"]


def test_HumanNameModel():
    data = {
        "family": "Doe",
        "given": ["John"],
        "prefix": ["Mr."]
    }
    name = HumanNameModel(**data)
    name = name.model_dump(by_alias=True)
    assert name['family'] == "Doe"
    assert name['given'] == ["John"]


def test_ContactPointModel():
    data = {
        "system": "phone",
        "value": "1234567890",
        "use": "home"
    }
    contact = ContactPointModel(**data)
    contact = contact.model_dump(by_alias=True)
    assert contact['system'] == "phone"
    assert contact['value'] == "1234567890"


def test_AddressModel():
    data = {
        "use": "home",
        "type": "postal",
        "text": "123 Main St",
        "line": ["Apt 1"],
        "city": "Anytown",
        "district": "Any County",
        "state": "NY",
        "postalCode": "12345",
        "country": "US"
    }
    address = AddressModel(**data)
    address = address.model_dump(by_alias=True)
    assert address['use'] == "home"
    assert address['line'] == ["Apt 1"]
    assert address['city'] == "Anytown"
    assert address['state'] == "NY"
    assert address['postalCode'] == "12345"
    assert address['country'] == "US"

