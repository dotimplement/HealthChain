import pytest
from unittest.mock import patch, MagicMock

from healthchain.sandbox.use_cases import clindoc
from healthchain.sandbox.use_cases.clindoc import (
    ClinDocRequestConstructor,
    ClinicalDocumentation,
)
from healthchain.sandbox.workflows import Workflow, UseCaseType
from healthchain.service.endpoints import ApiProtocol
from healthchain.fhir import create_document_reference


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
    doc_ref = create_document_reference(
        data=xml_content, content_type="text/xml", description="Test CDA Document"
    )

    # Mock CdaRequest.from_dict to avoid actual parsing
    with patch("healthchain.models.CdaRequest.from_dict") as mock_from_dict:
        mock_from_dict.return_value = MagicMock()

        # Construct the request
        constructor.construct_request(doc_ref, Workflow.sign_note_inpatient)

        # Verify CdaRequest.from_dict was called with modified envelope
        mock_from_dict.assert_called_once()
        # XML should be base64 encoded
        assert (
            "urn:Document"
            in mock_envelope["soapenv:Envelope"]["soapenv:Body"]["urn:ProcessDocument"]
        )


def test_clindoc_request_construction_no_xml():
    """Test CDA request construction when no XML content is found"""
    constructor = ClinDocRequestConstructor()

    # Create a DocumentReference without XML content
    doc_ref = create_document_reference(
        data="Not XML content",
        content_type="text/plain",
        description="Test non-XML Document",
    )

    mock_warning = MagicMock()
    clindoc.log.warning = mock_warning

    result = constructor.construct_request(doc_ref, Workflow.sign_note_inpatient)
    assert result is None
    mock_warning.assert_called_once()


def test_clinical_documentation_init():
    """Test ClinicalDocumentation initialization"""
    # Test with default parameters
    clindoc = ClinicalDocumentation()
    assert clindoc.type == UseCaseType.clindoc
    assert isinstance(clindoc.strategy, ClinDocRequestConstructor)
    assert clindoc._path == "/notereader/"

    # Test with custom path
    custom_path = "/api/notereader/"
    clindoc_custom = ClinicalDocumentation(path=custom_path)
    assert clindoc_custom._path == custom_path


def test_clinical_documentation_properties():
    """Test ClinicalDocumentation properties"""
    clindoc = ClinicalDocumentation()

    # Check properties
    assert clindoc.description == "Clinical documentation (NoteReader)"
    assert clindoc.type == UseCaseType.clindoc
    assert isinstance(clindoc.strategy, ClinDocRequestConstructor)
