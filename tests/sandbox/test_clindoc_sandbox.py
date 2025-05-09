from unittest.mock import patch, MagicMock
from fastapi import FastAPI

import healthchain as hc
from healthchain.gateway.services.notereader import NoteReaderService
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.sandbox.use_cases import ClinicalDocumentation
from healthchain.fhir import create_document_reference


def test_notereader_sandbox_integration():
    """Test NoteReaderService integration with sandbox decorator"""
    app = FastAPI()
    note_service = NoteReaderService()

    # Register a method handler for the service
    @note_service.method("ProcessDocument")
    def process_document(cda_request: CdaRequest) -> CdaResponse:
        return CdaResponse(document="<processed>document</processed>", error=None)

    note_service.add_to_app(app)

    # Define a sandbox class that uses the NoteReader service
    @hc.sandbox("http://localhost:8000/")
    class TestNotereaderSandbox(ClinicalDocumentation):
        def __init__(self):
            super().__init__()
            self.test_document = "<test>document</test>"

        @hc.ehr(workflow="sign-note-inpatient")
        def load_document_reference(self):
            return create_document_reference(
                data=self.test_document,
                content_type="text/xml",
                description="Test document",
            )

    # Create an instance of the sandbox
    sandbox_instance = TestNotereaderSandbox()

    # Patch the client request method to avoid actual HTTP requests
    with patch.object(sandbox_instance, "_client") as mock_client:
        mock_response = MagicMock()
        mock_response.text = "<processed>document</processed>"
        mock_client.send_soap_request.return_value = mock_response

        # Verify the sandbox can be initialized with the workflow
        assert hasattr(sandbox_instance, "load_document_reference")


def test_notereader_sandbox_workflow_execution():
    """Test executing a NoteReader workflow in the sandbox"""

    # Create a sandbox class with NoteReader
    @hc.sandbox("http://localhost:8000/")
    class TestNotereaderWithData(ClinicalDocumentation):
        def __init__(self):
            super().__init__()
            self.data_processed = False

        @hc.ehr(workflow="sign-note-inpatient")
        def get_clinical_document(self):
            return create_document_reference(
                data="<ClinicalDocument>Test content</ClinicalDocument>",
                content_type="text/xml",
                description="Test CDA document",
            )

    # Create sandbox instance
    sandbox = TestNotereaderWithData()

    # Mock the client to avoid HTTP requests
    with patch.object(sandbox, "_client") as mock_client:
        # Mock response from server
        mock_response = MagicMock()
        mock_response.text = "<processed>document</processed>"
        mock_response.status_code = 200
        mock_client.send_soap_request.return_value = mock_response

        # Set up the sandbox with correct attributes for testing
        sandbox._client.workflow = MagicMock()
        sandbox._client.workflow.value = "sign-note-inpatient"
