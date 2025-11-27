import pytest
from unittest.mock import MagicMock, patch

from healthchain.sandbox.requestconstructors import (
    CdsRequestConstructor,
    ClinDocRequestConstructor,
)
from healthchain.sandbox.workflows import Workflow
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

    # Create a prefetch dict
    prefetch = {"patient": create_bundle()}

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
    """Test validation error handling in CdsRequestConstructor"""
    constructor = CdsRequestConstructor()

    # Test with invalid workflow - should raise ValueError
    with pytest.raises(ValueError):
        # Invalid workflow
        invalid_workflow = MagicMock()
        invalid_workflow.value = "invalid-workflow"
        constructor.construct_request(
            prefetch_data={"patient": create_bundle()}, workflow=invalid_workflow
        )


def test_cds_request_construction():
    """Test request construction in CdsRequestConstructor"""
    constructor = CdsRequestConstructor()

    # Create a bundle and prefetch dict
    bundle = create_bundle()
    prefetch = {"patient": bundle}

    # Construct a request
    request = constructor.construct_request(
        prefetch_data=prefetch,
        workflow=Workflow.patient_view,
        context={"patientId": "test-patient-123"},
    )

    # Verify request properties
    assert request.hook == "patient-view"
    assert request.context.patientId == "test-patient-123"
    assert request.prefetch == prefetch


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


def test_clindoc_request_handles_malformed_xml():
    """ClinDocRequestConstructor rejects malformed XML and returns None."""
    constructor = ClinDocRequestConstructor()

    # Test with invalid XML
    malformed_xml = "<ClinicalDocument><unclosed>tag"
    result = constructor.construct_request(malformed_xml, Workflow.sign_note_inpatient)

    assert result is None


def test_clindoc_request_rejects_non_string_input():
    """ClinDocRequestConstructor raises ValueError for non-string data."""
    constructor = ClinDocRequestConstructor()

    with pytest.raises(ValueError, match="Expected str"):
        constructor.construct_request({"not": "a string"}, Workflow.sign_note_inpatient)

    with pytest.raises(ValueError, match="Expected str"):
        constructor.construct_request(123, Workflow.sign_note_inpatient)


def test_clindoc_request_missing_soap_envelope_key():
    """ClinDocRequestConstructor raises ValueError when SOAP template missing required key."""
    with patch.object(ClinDocRequestConstructor, "_load_soap_envelope") as mock_load:
        # Mock envelope without required key
        mock_load.return_value = {"soapenv:Envelope": {"soapenv:Body": {}}}

        constructor = ClinDocRequestConstructor()
        xml_content = "<ClinicalDocument>Test</ClinicalDocument>"

        with pytest.raises(ValueError, match="Key 'urn:Document' missing"):
            constructor.construct_request(xml_content, Workflow.sign_note_inpatient)


def test_cds_request_construction_with_custom_context():
    """CdsRequestConstructor includes custom context parameters in request."""
    constructor = CdsRequestConstructor()
    bundle = create_bundle()
    prefetch = {"patient": bundle}

    # Test with custom context
    custom_context = {"patientId": "patient-123", "encounterId": "encounter-456"}

    request = constructor.construct_request(
        prefetch_data=prefetch, workflow=Workflow.patient_view, context=custom_context
    )

    assert request.context.patientId == "patient-123"
    assert request.context.encounterId == "encounter-456"


def test_cds_request_validates_workflow_for_clinical_doc():
    """CdsRequestConstructor rejects ClinicalDocumentation workflows."""
    constructor = CdsRequestConstructor()
    prefetch = {"patient": create_bundle()}

    # Should reject sign-note workflows
    with pytest.raises(ValueError, match="Invalid workflow"):
        constructor.construct_request(
            prefetch_data=prefetch, workflow=Workflow.sign_note_inpatient
        )
