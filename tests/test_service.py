from unittest.mock import patch
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from healthchain.service import Service
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.use_cases.clindoc import ClinicalDocumentation

cds = ClinicalDecisionSupport()
cds_service = Service(endpoints=cds.endpoints)
cds_client = TestClient(cds_service.app)

clindoc = ClinicalDocumentation()
clindoc_service = Service(endpoints=clindoc.endpoints)
clindoc_client = TestClient(clindoc_service.app)


def test_cds_discover():
    response = cds_client.get("/cds-services")
    assert response.status_code == 200
    assert response.json() == {"services": []}


def test_cds_service(test_cds_request):
    response = cds_client.post(
        "/cds-services/1", json=jsonable_encoder(test_cds_request)
    )
    assert response.status_code == 200
    assert response.json() == {"cards": []}


@patch(
    "healthchain.use_cases.clindoc.ClinicalDocumentation.process_notereader_document"
)
def test_clindoc_process_document(mock_process, test_cda_response, test_soap_request):
    mock_process.return_value = test_cda_response

    headers = {"Content-Type": "text/xml; charset=utf-8"}
    response = clindoc_client.post(
        "/notereader", content=test_soap_request.document, headers=headers
    )

    assert response.status_code == 200
    assert (
        response.text
        == "<?xml version='1.0' encoding='UTF-8'?>\n<soap11env:Envelope xmlns:soap11env=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:tns=\"urn:epic-com:Common.2013.Services\"><soap11env:Body><tns:ProcessDocumentResponse><tns:ProcessDocumentResult><tns:Document></tns:Document></tns:ProcessDocumentResult></tns:ProcessDocumentResponse></soap11env:Body></soap11env:Envelope>"
    )
