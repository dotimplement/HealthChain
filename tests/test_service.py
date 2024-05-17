from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from healthchain.service.service import Service
from healthchain.use_cases.cds import ClinicalDecisionSupport

cds = ClinicalDecisionSupport()
service = Service(endpoints=cds.endpoints)

client = TestClient(service.app)


def test_cds_discover():
    response = client.get("/cds-services")
    assert response.status_code == 200
    assert response.json() == {"services": []}


def test_cds_service(test_cds_request):
    response = client.post("/cds-services/1", json=jsonable_encoder(test_cds_request))
    assert response.status_code == 200
    assert response.json() == {"cards": []}
