from healthchain.fhir_resources.practitioner import Practitioner


def test_PractitionerModel():
    data = {
        "resourceType": "Practitioner",
        "name": [{"family": "Doe", "given": ["John"], "prefix": ["Mr."]}],
        "birthDate": "1980-01-01",
        "qualification": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://example.org",
                            "code": "12345",
                            "display": "Qualification 1",
                        }
                    ],
                    "text": "Qualification 1",
                },
                "period": {"start": "2010-01-01", "end": "2015-01-01"},
            }
        ],
        "communication": [
            {
                "language": {
                    "coding": [
                        {
                            "system": "http://example.org",
                            "code": "en",
                            "display": "English",
                        }
                    ],
                    "text": "English",
                }
            }
        ],
    }

    practitioner = Practitioner(**data)
    practitioner = practitioner.model_dump(by_alias=True)
    assert practitioner["resourceType"] == "Practitioner"
    assert practitioner["name"][0]["given"] == ["John"]
    assert practitioner["birthDate"] == "1980-01-01"
    assert practitioner["qualification"][0]["code"]["coding"][0]["code"] == "12345"
