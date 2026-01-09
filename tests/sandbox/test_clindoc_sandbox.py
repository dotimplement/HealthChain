import base64
from unittest.mock import patch, MagicMock

from healthchain.sandbox import SandboxClient
from healthchain.gateway.soap.notereader import NoteReaderService
from healthchain.gateway.api import HealthChainAPI
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse


def test_notereader_sandbox_integration():
    """Test NoteReaderService integration with SandboxClient"""
    # Use HealthChainAPI
    app = HealthChainAPI()
    note_service = NoteReaderService()

    # Register a method handler for the service
    @note_service.method("ProcessDocument")
    def process_document(cda_request: CdaRequest) -> CdaResponse:
        return CdaResponse(document="<processed>document</processed>", error=None)

    # Register service with HealthChainAPI
    app.register_service(note_service, "/notereader")

    # Create SandboxClient for SOAP/CDA
    client = SandboxClient(
        url="http://localhost:8000/notereader/?wsdl",
        workflow="sign-note-inpatient",
        protocol="soap",
    )

    # Load test document
    test_document = "<test>document</test>"
    client._construct_request(test_document)

    # Verify request was constructed
    assert len(client.requests) == 1

    # Mock HTTP response with proper SOAP envelope structure
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Create proper SOAP response with base64-encoded CDA
        cda_content = "<processed>document</processed>"
        encoded_cda = base64.b64encode(cda_content.encode("utf-8")).decode("utf-8")
        soap_response = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                          xmlns:tns="urn:epic-com:Common.2013.Services">
            <soapenv:Body>
                <tns:ProcessDocumentResponse>
                    <tns:Document>{encoded_cda}</tns:Document>
                </tns:ProcessDocumentResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        mock_response = MagicMock()
        mock_response.text = soap_response
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        # Send requests
        responses = client.send_requests()

        # Verify response
        assert len(responses) == 1
        assert "<processed>document</processed>" in responses[0]


def test_notereader_sandbox_workflow_execution():
    """Test executing a NoteReader workflow with SandboxClient"""
    # Create SandboxClient
    client = SandboxClient(
        url="http://localhost:8000/notereader/?wsdl",
        workflow="sign-note-inpatient",
        protocol="soap",
    )

    # Load clinical document
    clinical_document = "<ClinicalDocument>Test content</ClinicalDocument>"
    client._construct_request(clinical_document)

    # Verify request was constructed
    assert len(client.requests) == 1

    # Mock HTTP response with proper SOAP envelope structure
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Create proper SOAP response with base64-encoded CDA
        cda_content = "<processed>document</processed>"
        encoded_cda = base64.b64encode(cda_content.encode("utf-8")).decode("utf-8")
        soap_response = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                          xmlns:tns="urn:epic-com:Common.2013.Services">
            <soapenv:Body>
                <tns:ProcessDocumentResponse>
                    <tns:Document>{encoded_cda}</tns:Document>
                </tns:ProcessDocumentResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        mock_response = MagicMock()
        mock_response.text = soap_response
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        # Send requests and verify
        responses = client.send_requests()
        assert len(responses) == 1
        assert "<processed>document</processed>" in responses[0]
