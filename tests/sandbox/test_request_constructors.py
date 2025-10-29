import pytest
from unittest.mock import MagicMock, patch

from healthchain.sandbox.requestconstructors import (
    CdsRequestConstructor,
    ClinDocRequestConstructor,
)
from healthchain.sandbox.workflows import Workflow
from healthchain.models.hooks.prefetch import Prefetch
from healthchain.sandbox.base import ApiProtocol
from healthchain.fhir import create_bundle


def test_cds_request_constructor_init():
    """Test CdsRequestConstructor initialization"""
    constructor = CdsRequestConstructor()

    # Check protocol setting
    assert constructor.api_protocol == ApiProtocol.rest

    # Check context mapping
    assert Workflow.patient_view in constructor.context_mapping
    assert Workflow.order_select in constructor.context_mapping
    assert Workflow.order_sign in constructor.context_mapping
    assert Workflow.encounter_discharge in constructor.context_mapping


def test_cds_request_constructor_validation():
    """Test validation of workflows in CdsRequestConstructor"""
    constructor = CdsRequestConstructor()

    # Create a prefetch object
    prefetch = Prefetch(prefetch={"patient": create_bundle()})

    # Test with valid workflow
    valid_workflow = Workflow.patient_view
    # Should not raise error
    constructor.construct_request(prefetch_data=prefetch, workflow=valid_workflow)

    # Test with invalid workflow - should raise ValueError
    with pytest.raises(ValueError):
        # Not a real workflow
        invalid_workflow = MagicMock()
        invalid_workflow.value = "invalid-workflow"
        constructor.construct_request(prefetch_data=prefetch, workflow=invalid_workflow)


def test_cds_request_constructor_type_error():
    """Test type error handling in CdsRequestConstructor"""
    constructor = CdsRequestConstructor()

    # Test with invalid prefetch data type - should raise TypeError
    with pytest.raises(TypeError):
        # Not a Prefetch object
        invalid_prefetch = {"patient": create_bundle()}
        constructor.construct_request(
            prefetch_data=invalid_prefetch, workflow=Workflow.patient_view
        )


def test_cds_request_construction():
    """Test request construction in CdsRequestConstructor"""
    constructor = CdsRequestConstructor()

    # Create a bundle and prefetch
    bundle = create_bundle()
    prefetch = Prefetch(prefetch={"patient": bundle})

    # Construct a request
    request = constructor.construct_request(
        prefetch_data=prefetch,
        workflow=Workflow.patient_view,
        context={"patientId": "test-patient-123"},
    )

    # Verify request properties
    assert request.hook == "patient-view"
    assert request.context.patientId == "test-patient-123"
    assert request.prefetch == prefetch.prefetch


def test_clindoc_request_constructor_init():
    """Test ClinDocRequestConstructor initialization"""
    constructor = ClinDocRequestConstructor()

    # Check protocol setting
    assert constructor.api_protocol == ApiProtocol.soap

    # Check SOAP envelope was loaded
    assert constructor.soap_envelope is not None
    assert isinstance(constructor.soap_envelope, dict)


@patch("pkgutil.get_data")
def test_clindoc_request_constructor_load_envelope(mock_get_data):
    """Test loading the SOAP envelope template"""
    # Mock data returned from pkgutil
    mock_get_data.return_value = (
        b"<soapenv:Envelope><soapenv:Body></soapenv:Body></soapenv:Envelope>"
    )

    ClinDocRequestConstructor()

    # Check if pkgutil.get_data was called with correct parameters
    mock_get_data.assert_called_once_with("healthchain", "templates/soap_envelope.xml")


def test_clindoc_request_constructor_not_implemented():
    """Test not implemented methods raise appropriate exceptions"""
    constructor = ClinDocRequestConstructor()

    # Test that method raises NotImplementedError
    with pytest.raises(NotImplementedError):
        constructor.construct_cda_xml_document()


@patch.object(ClinDocRequestConstructor, "_load_soap_envelope")
def test_clindoc_request_construction(mock_load_envelope):
    """Test CDA request construction from DocumentReference"""
    # Create mock SOAP envelope
    mock_envelope = {
        "soapenv:Envelope": {
            "soapenv:Body": {"urn:ProcessDocument": {"urn:Document": ""}}
        }
    }
    mock_load_envelope.return_value = mock_envelope

    constructor = ClinDocRequestConstructor()

    # Create a DocumentReference with XML content
    xml_content = "<ClinicalDocument>Test Document</ClinicalDocument>"

    # Mock CdaRequest.from_dict to avoid actual parsing
    with patch("healthchain.models.CdaRequest.from_dict") as mock_from_dict:
        mock_from_dict.return_value = MagicMock()

        # Construct the request
        constructor.construct_request(xml_content, Workflow.sign_note_inpatient)

        # Verify CdaRequest.from_dict was called with modified envelope
        mock_from_dict.assert_called_once()
        # XML should be base64 encoded
        assert (
            "urn:Document"
            in mock_envelope["soapenv:Envelope"]["soapenv:Body"]["urn:ProcessDocument"]
        )
