from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from .conftest import synth_data
from healthchain.decorators import sandbox, ehr, api
from healthchain.use_cases.cds import ClinicalDecisionSupport


@sandbox
class myCDS(ClinicalDecisionSupport):
    def __init__(self) -> None:
        self.data_generator = None

    # decorator sets up an instance of ehr configured with use case CDS
    @ehr(workflow="encounter-discharge", num=3)
    def load_data(self, data_spec):
        # data = "hello, " + data_spec
        data = synth_data(
            context={
                "userId": "Practitioner/123",
                "patientId": data_spec,
                "encounterId": "123",
            },
            uuid="29e93987-c345-4cb7-9a92-b5136289c2a4",
            prefetch={},
        )
        return data

    @api
    def llm(self, text: str):
        return {
            "cards": [
                {
                    "summary": "example",
                    "indicator": "info",
                    "source": {"label": "website"},
                }
            ]
        }


cds = myCDS()

client = TestClient(cds.service.app)


def test_cds_discover():
    response = client.get("/cds-services")
    assert response.status_code == 200
    assert response.json() == {
        "services": [
            {
                "hook": "encounter-discharge",
                "description": "A test CDS hook service.",
                "id": "1",
            }
        ]
    }


def test_cds_service(test_cds_request):
    response = client.post("/cds-services/1", json=jsonable_encoder(test_cds_request))
    assert response.status_code == 200
    assert response.json() == {
        "cards": [
            {"summary": "example", "indicator": "info", "source": {"label": "website"}}
        ]
    }


# def test_whole_sandbox():
#     cds.start_sandbox()
#     assert cds.responses == [
#         {
#             "cards": [
#                 {
#                     "summary": "example",
#                     "indicator": "info",
#                     "source": {"label": "website"},
#                 }
#             ]
#         },
#         {
#             "cards": [
#                 {
#                     "summary": "example",
#                     "indicator": "info",
#                     "source": {"label": "website"},
#                 }
#             ]
#         },
#         {
#             "cards": [
#                 {
#                     "summary": "example",
#                     "indicator": "info",
#                     "source": {"label": "website"},
#                 }
#             ]
#         },
#     ]
