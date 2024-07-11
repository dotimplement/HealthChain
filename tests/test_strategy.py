import pytest

from unittest.mock import patch, MagicMock
from healthchain.workflows import Workflow
from healthchain.models import CDSRequest
from healthchain.models.hooks import PatientViewContext
from healthchain.models import CcdData, CdaRequest
from healthchain.use_cases.clindoc import ClinicalDocumentationStrategy


def test_valid_data_request_construction(cds_strategy, valid_data):
    with patch.object(CDSRequest, "__init__", return_value=None) as mock_init:
        cds_strategy.construct_request(valid_data, Workflow.patient_view)
        mock_init.assert_called_once_with(
            hook=Workflow.patient_view.value,
            context=PatientViewContext(userId="Practitioner/123", patientId="123"),
            prefetch={"entry": [{}]},
        )


def test_invalid_data_raises_error(cds_strategy, invalid_data):
    with pytest.raises(ValueError):
        # incorrect keys passed in
        cds_strategy.construct_request(invalid_data, Workflow.patient_view)

    with pytest.raises(ValueError):
        # correct keys but invalid data
        invalid_data.context = {"userId": "Practitioner"}
        cds_strategy.construct_request(invalid_data, Workflow.patient_view)


def test_context_mapping(cds_strategy, valid_data):
    with patch.dict(
        cds_strategy.context_mapping,
        {
            Workflow.patient_view: MagicMock(
                spec=PatientViewContext,
                return_value=PatientViewContext(
                    userId="Practitioner/123", patientId="123"
                ),
            )
        },
    ):
        cds_strategy.construct_request(data=valid_data, workflow=Workflow.patient_view)
        cds_strategy.context_mapping[Workflow.patient_view].assert_called_once_with(
            **valid_data.context
        )


def test_workflow_validation_decorator(cds_strategy, valid_data):
    with pytest.raises(ValueError) as excinfo:
        cds_strategy.construct_request(Workflow.sign_note_inpatient, valid_data)
    assert "Invalid workflow" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        cds_strategy.construct_request(
            data=valid_data, workflow=Workflow.sign_note_inpatient
        )
    assert "Invalid workflow" in str(excinfo.value)

    assert cds_strategy.construct_request(valid_data, Workflow.patient_view)


def test_construct_request_with_cda_xml():
    strategy = ClinicalDocumentationStrategy()
    data = CcdData(cda_xml="<CDA XML>")
    workflow = Workflow.sign_note_inpatient

    request = strategy.construct_request(data, workflow)

    assert isinstance(request, CdaRequest)
    assert (
        request.document
        == '<?xml version="1.0" encoding="utf-8"?>\n<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:epic-com:Common.2013.Services" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header></soapenv:Header><soapenv:Body><urn:ProcessDocument><urn:SessionID>0000-0000-0000-0000</urn:SessionID><urn:WorkType>2</urn:WorkType><urn:OrganizationID>UCLH</urn:OrganizationID><urn:Document>PENEQSBYTUw+</urn:Document></urn:ProcessDocument></soapenv:Body></soapenv:Envelope>'
    )


def test_construct_request_without_cda_xml(caplog):
    strategy = ClinicalDocumentationStrategy()
    data = CcdData()
    workflow = Workflow.sign_note_inpatient

    strategy.construct_request(data, workflow)

    assert (
        "Data generation methods for CDA documents not implemented yet!" in caplog.text
    )


def test_construct_request(test_ccd_data):
    strategy = ClinicalDocumentationStrategy()
    data = CcdData(cda_xml="<CDA XML>")
    workflow = Workflow.sign_note_inpatient

    request = strategy.construct_request(data, workflow)
    assert isinstance(request, CdaRequest)
    assert "urn:Document" in request.document
