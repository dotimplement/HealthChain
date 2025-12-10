"""
Tests for FastAPI-based SOAP server implementation.

These tests replace the old Spyne-based tests and verify the new
FastAPI SOAP router functionality.
"""

import base64
import pytest
import lxml.etree as ET
from fastapi import FastAPI
from fastapi.testclient import TestClient

from healthchain.gateway.soap.notereader import NoteReaderService, NoteReaderConfig
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse


# Namespace mappings for parsing SOAP responses
SOAP_NAMESPACES = {
    "soap": "http://schemas.xmlsoap.org/soap/envelope/",
    "tns": "urn:epic-com:Common.2013.Services",
}


def parse_soap_response(response_content: bytes) -> ET._Element:
    """Parse SOAP response XML and return the root element"""
    return ET.fromstring(response_content)


def get_document_from_response(response_content: bytes) -> str:
    """Extract and decode the Document element from SOAP response"""
    xml = parse_soap_response(response_content)
    doc_element = xml.find(".//tns:Document", SOAP_NAMESPACES)
    if doc_element is not None and doc_element.text:
        # Document is base64 encoded per WSDL
        return base64.b64decode(doc_element.text).decode("utf-8")
    return ""


def get_error_from_response(response_content: bytes) -> str:
    """Extract the Error element text from SOAP response"""
    xml = parse_soap_response(response_content)
    error_element = xml.find(".//tns:Error", SOAP_NAMESPACES)
    if error_element is not None:
        return error_element.text or ""
    return ""


@pytest.fixture
def notereader_service():
    """Create a NoteReaderService instance for testing"""
    return NoteReaderService(use_events=False)


@pytest.fixture
def app_with_soap(notereader_service):
    """Create a FastAPI app with SOAP service mounted"""
    app = FastAPI()

    # Register a basic handler
    @notereader_service.method("ProcessDocument")
    def process_document(request: CdaRequest) -> CdaResponse:
        return CdaResponse(document=f"Processed: {request.document}", error=None)

    # Mount the router
    router = notereader_service.create_fastapi_router()
    app.include_router(router, prefix="/soap")

    return app


@pytest.fixture
def client(app_with_soap):
    """Create a test client"""
    return TestClient(app_with_soap)


def build_soap_request(
    session_id=None, work_type=None, organization_id=None, document=None
):
    """Helper to build SOAP request XML - only includes provided parameters"""
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">',
        "  <soap:Body>",
        '    <ProcessDocument xmlns="urn:epic-com:Common.2013.Services">',
    ]

    if session_id is not None:
        parts.append(f"      <SessionID>{session_id}</SessionID>")
    if work_type is not None:
        parts.append(f"      <WorkType>{work_type}</WorkType>")
    if organization_id is not None:
        parts.append(f"      <OrganizationID>{organization_id}</OrganizationID>")
    if document is not None:
        parts.append(f"      <Document>{document}</Document>")

    parts.extend(["    </ProcessDocument>", "  </soap:Body>", "</soap:Envelope>"])

    return "\n".join(parts)


class TestSOAPValidation:
    """Test SOAP request validation"""

    def test_debug_request(self, client):
        """Debug test to see what's being sent and received"""
        soap_request = build_soap_request(
            session_id="12345",
            work_type="TestWork",
            organization_id="OrgID",
            document="<xml>test</xml>",
        )

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 200

    def test_missing_session_id(self, client):
        """Test that missing SessionID returns SOAP fault"""
        soap_request = build_soap_request(
            work_type="WorkType", organization_id="OrgID", document="<xml>test</xml>"
        )

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 400
        assert b"faultcode" in response.content
        assert b"SessionID" in response.content

    def test_missing_work_type(self, client):
        """Test that missing WorkType returns SOAP fault"""
        soap_request = build_soap_request(
            session_id="12345", organization_id="OrgID", document="<xml>test</xml>"
        )

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 400
        assert b"faultcode" in response.content
        assert b"WorkType" in response.content

    def test_missing_organization_id(self, client):
        """Test that missing OrganizationID returns SOAP fault"""
        soap_request = build_soap_request(
            session_id="12345", work_type="WorkType", document="<xml>test</xml>"
        )

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 400
        assert b"faultcode" in response.content
        assert b"OrganizationID" in response.content

    def test_missing_document(self, client):
        """Test that missing Document returns SOAP fault"""
        soap_request = build_soap_request(
            session_id="12345", work_type="WorkType", organization_id="OrgID"
        )

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 400
        assert b"faultcode" in response.content
        assert b"Document" in response.content

    def test_invalid_xml(self, client):
        """Test that invalid XML returns SOAP fault"""
        invalid_xml = "This is not XML"

        response = client.post("/soap/", content=invalid_xml)

        assert response.status_code == 400
        assert b"faultcode" in response.content
        assert b"Invalid XML" in response.content

    def test_missing_soap_body(self, client):
        """Test that missing SOAP body returns fault"""
        soap_request = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
</soap:Envelope>"""

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 400
        assert b"Missing SOAP Body" in response.content


class TestProcessDocument:
    """Test ProcessDocument operation"""

    def test_successful_request(self, client):
        """Test successful document processing"""
        import base64
        import lxml.etree as ET

        # Encode the document as base64 (as required by WSDL)
        plain_document = "<ClinicalDocument>test data</ClinicalDocument>"
        encoded_document = base64.b64encode(plain_document.encode("utf-8")).decode(
            "ascii"
        )

        soap_request = build_soap_request(
            session_id="12345",
            work_type="TestWork",
            organization_id="OrgID",
            document=encoded_document,  # Send base64-encoded
        )

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 200
        assert b"ProcessDocumentResponse" in response.content

        # Parse response to check structure
        xml = ET.fromstring(response.content)

        # Find the Document element (it's base64 encoded per WSDL)
        namespaces = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "tns": "urn:epic-com:Common.2013.Services",
        }

        doc_element = xml.find(".//tns:Document", namespaces)
        assert doc_element is not None, "Document element should be present"

        # Decode base64 content
        if doc_element.text:
            decoded = base64.b64decode(doc_element.text).decode("utf-8")
            assert (
                "Processed:" in decoded
            ), f"Expected 'Processed:' in decoded document, got: {decoded}"
            assert plain_document in decoded, "Expected original document in response"

    def test_handler_returns_error(self):
        """Test when handler returns a CdaResponse with error"""
        app = FastAPI()
        service = NoteReaderService(use_events=False)

        @service.method("ProcessDocument")
        def error_handler(request: CdaRequest) -> CdaResponse:
            return CdaResponse(document="", error="Processing failed")

        router = service.create_fastapi_router()
        app.include_router(router, prefix="/soap")
        client = TestClient(app)

        soap_request = build_soap_request(
            session_id="12345",
            work_type="TestWork",
            organization_id="OrgID",
            document="<xml>test</xml>",
        )

        response = client.post("/soap/", content=soap_request)

        # Should return 200 with error in response
        assert response.status_code == 200
        assert b"<Error>" in response.content or b"<tns:Error>" in response.content
        assert b"Processing failed" in response.content

    def test_handler_raises_exception(self):
        """Test when handler raises an exception"""
        app = FastAPI()
        service = NoteReaderService(use_events=False)

        @service.method("ProcessDocument")
        def failing_handler(request: CdaRequest) -> CdaResponse:
            raise ValueError("Something went wrong")

        router = service.create_fastapi_router()
        app.include_router(router, prefix="/soap")
        client = TestClient(app)

        soap_request = build_soap_request(
            session_id="12345",
            work_type="TestWork",
            organization_id="OrgID",
            document="<xml>test</xml>",
        )

        response = client.post("/soap/", content=soap_request)

        # Should return 200 with error in response (error handled gracefully)
        assert response.status_code == 200
        assert b"<Error>" in response.content or b"<tns:Error>" in response.content
        assert b"Something went wrong" in response.content

    def test_document_with_special_characters(self, client):
        """Test document with XML special characters"""
        # Note: In real SOAP, this would be CDATA or encoded
        soap_request = build_soap_request(
            session_id="12345",
            work_type="TestWork",
            organization_id="OrgID",
            document="&lt;xml&gt;test&lt;/xml&gt;",
        )

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 200


class TestServiceConfiguration:
    """Test service configuration and setup"""

    def test_no_handler_registered(self):
        """Test that creating router without handler raises error"""
        service = NoteReaderService(use_events=False)

        with pytest.raises(ValueError) as exc_info:
            service.create_fastapi_router()

        assert "No ProcessDocument handler registered" in str(exc_info.value)

    def test_custom_config(self):
        """Test service with custom configuration"""
        config = NoteReaderConfig(
            service_name="CustomService",
            namespace="urn:custom:namespace",
            system_type="CUSTOM_SYSTEM",
        )
        service = NoteReaderService(config=config, use_events=False)

        metadata = service.get_metadata()

        assert metadata["soap_service"] == "CustomService"
        assert metadata["namespace"] == "urn:custom:namespace"
        assert metadata["system_type"] == "CUSTOM_SYSTEM"

    def test_handler_decorator(self):
        """Test that method decorator properly registers handler"""
        service = NoteReaderService(use_events=False)

        @service.method("ProcessDocument")
        def my_handler(request: CdaRequest) -> CdaResponse:
            return CdaResponse(document="test", error=None)

        # Should be able to create router now
        router = service.create_fastapi_router()
        assert router is not None

    def test_no_events_when_disabled(self):
        """Test that events are not emitted when disabled"""
        service = NoteReaderService(use_events=False)

        # Mock the emit_event method to track calls
        events_emitted = []

        def mock_emit_event(*args, **kwargs):
            events_emitted.append({"args": args, "kwargs": kwargs})

        service.events.emit_event = mock_emit_event

        @service.method("ProcessDocument")
        def handler(request: CdaRequest) -> CdaResponse:
            return CdaResponse(document="processed", error=None)

        app = FastAPI()
        router = service.create_fastapi_router()
        app.include_router(router, prefix="/soap")
        client = TestClient(app)

        soap_request = build_soap_request(
            session_id="12345",
            work_type="TestWork",
            organization_id="OrgID",
            document="<xml>test</xml>",
        )

        response = client.post("/soap/", content=soap_request)

        assert response.status_code == 200

        # When use_events=False, emit_event should not be called
        assert (
            len(events_emitted) == 0
        ), f"Expected 0 events when disabled, got {len(events_emitted)}"


class TestDocumentCoercion:
    """Test document value coercion"""

    def test_base64_encoded_document(self, client):
        """Test handling of base64-encoded documents"""
        import base64

        original_doc = "<ClinicalDocument>test</ClinicalDocument>"
        encoded_doc = base64.b64encode(original_doc.encode()).decode()

        soap_request = build_soap_request(
            session_id="12345",
            work_type="TestWork",
            organization_id="OrgID",
            document=encoded_doc,
        )

        response = client.post("/soap/", content=soap_request)

        # Should handle base64 decoding
        assert response.status_code == 200
