from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from healthchain.clients import ehr
from healthchain.decorators import sandbox, api
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.models import Card

from .conftest import MockDataGenerator


@sandbox
class myCDS(ClinicalDecisionSupport):
    def __init__(self) -> None:
        self.data_generator = MockDataGenerator()

    # decorator sets up an instance of ehr configured with use case CDS
    @ehr(workflow="encounter-discharge", num=3)
    def load_data(self):
        return self.data_generator.data

    @api
    def llm(self, text: str):
        return [
            Card(
                summary=self.data_generator.data.prefetch.condition,
                indicator="info",
                source={"label": "website"},
            )
        ]


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
            {"summary": "test", "indicator": "info", "source": {"label": "website"}}
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
