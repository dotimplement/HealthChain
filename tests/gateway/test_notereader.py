import pytest
from unittest.mock import MagicMock

from healthchain.gateway.soap.notereader import (
    NoteReaderService,
    NoteReaderConfig,
)
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from fastapi import APIRouter


@pytest.mark.parametrize(
    "config_args,expected_values",
    [
        # Default config via create()
        (
            {},
            {
                "service_name": "ICDSServices",
                "namespace": "urn:epic-com:Common.2013.Services",
                "system_type": "EHR_CDA",
                "default_mount_path": "/notereader",
            },
        ),
        # Custom config
        (
            {
                "service_name": "CustomService",
                "namespace": "urn:custom:namespace",
                "system_type": "CUSTOM_SYSTEM",
                "default_mount_path": "/custom-path",
            },
            {
                "service_name": "CustomService",
                "namespace": "urn:custom:namespace",
                "system_type": "CUSTOM_SYSTEM",
                "default_mount_path": "/custom-path",
            },
        ),
    ],
)
def test_notereader_service_configuration(config_args, expected_values):
    """NoteReaderService supports both default and custom configurations."""
    if config_args:
        config = NoteReaderConfig(**config_args)
        gateway = NoteReaderService(config=config)
    else:
        gateway = NoteReaderService.create()

    assert isinstance(gateway, NoteReaderService)
    assert isinstance(gateway.config, NoteReaderConfig)

    for attr_name, expected_value in expected_values.items():
        assert getattr(gateway.config, attr_name) == expected_value


def test_notereader_handler_registration_methods():
    """NoteReaderService supports both direct registration and decorator-based registration."""
    gateway = NoteReaderService()

    # Test direct registration
    mock_handler = MagicMock(return_value=CdaResponse(document="test", error=None))
    gateway.register_handler("ProcessDocument", mock_handler)
    assert "ProcessDocument" in gateway._handlers
    assert gateway._handlers["ProcessDocument"] == mock_handler

    # Test decorator registration
    @gateway.method("ProcessNotes")
    def process_notes(request):
        return CdaResponse(document="processed", error=None)

    assert "ProcessNotes" in gateway._handlers


def test_notereader_gateway_extract_request():
    """Test request extraction from parameters"""
    gateway = NoteReaderService()

    # Case 1: CdaRequest passed directly
    request = CdaRequest(document="<doc>test</doc>")
    extracted = gateway._extract_request("ProcessDocument", {"request": request})
    assert extracted == request

    # Case 2: CdaRequest as single parameter
    extracted = gateway._extract_request("ProcessDocument", {"param": request})
    assert extracted == request

    # Case 3: Build from params
    gateway.register_handler("ProcessDocument", lambda x: x)
    extracted = gateway._extract_request(
        "ProcessDocument", {"document": "<doc>test</doc>"}
    )
    assert isinstance(extracted, CdaRequest)
    assert extracted.document == "<doc>test</doc>"


def test_notereader_gateway_process_result():
    """Test processing results from handlers"""
    gateway = NoteReaderService()

    # Test with CdaResponse object
    response = CdaResponse(document="test", error=None)
    result = gateway._process_result(response)
    assert isinstance(result, CdaResponse)
    assert result.document == "test"

    # Test with dict
    result = gateway._process_result({"document": "test_dict", "error": None})
    assert isinstance(result, CdaResponse)
    assert result.document == "test_dict"


def test_notereader_gateway_create_fastapi_router():
    """Test that NoteReaderService creates a valid FastAPI router"""
    gateway = NoteReaderService()

    # Register required ProcessDocument handler
    @gateway.method("ProcessDocument")
    def process_document(request):
        return CdaResponse(document="processed", error=None)

    # Create FastAPI router
    router = gateway.create_fastapi_router()

    # Verify it returns an APIRouter
    assert isinstance(router, APIRouter)

    # Verify the router has routes registered
    routes = [route for route in router.routes]
    assert len(routes) > 0, "Router should have routes"

    # Verify POST route exists (for SOAP requests)
    post_routes = [r for r in routes if hasattr(r, "methods") and "POST" in r.methods]
    assert len(post_routes) > 0, "Router should have POST route for SOAP"

    # Verify GET route exists if WSDL is configured (for ?wsdl endpoint)
    get_routes = [r for r in routes if hasattr(r, "methods") and "GET" in r.methods]
    if gateway.config.wsdl_path:
        assert len(get_routes) > 0, "Router should have GET route for WSDL"

    # Verify we can get the default mount path from config
    config = gateway.config
    assert hasattr(config, "default_mount_path")
    assert config.default_mount_path == "/notereader"


def test_notereader_gateway_create_fastapi_router_without_handler():
    """Test that creating router without handler raises ValueError"""
    gateway = NoteReaderService()

    # Should raise error if no ProcessDocument handler registered
    with pytest.raises(ValueError, match="No ProcessDocument handler registered"):
        gateway.create_fastapi_router()


@pytest.mark.asyncio
async def test_notereader_gateway_soap_request_processing():
    """Test that the router can process a SOAP request"""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    gateway = NoteReaderService()

    @gateway.method("ProcessDocument")
    def process_document(request):
        # Return a CdaResponse with base64-encoded document
        import base64

        doc = base64.b64encode(b"<xml>processed</xml>").decode("ascii")
        return CdaResponse(document=doc, error=None)

    router = gateway.create_fastapi_router()
    app = FastAPI()
    app.include_router(router, prefix="/notereader")

    client = TestClient(app)

    # Create a minimal SOAP request
    soap_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:tns="urn:epic-com:Common.2013.Services">
        <soap:Body>
            <tns:ProcessDocument>
                <tns:SessionID>test-session</tns:SessionID>
                <tns:WorkType>1</tns:WorkType>
                <tns:OrganizationID>TEST</tns:OrganizationID>
                <tns:Document>PHhtbD50ZXN0PC94bWw+</tns:Document>
            </tns:ProcessDocument>
        </soap:Body>
    </soap:Envelope>"""

    response = client.post(
        "/notereader/", content=soap_request, headers={"Content-Type": "text/xml"}
    )

    assert response.status_code == 200
    assert b"ProcessDocumentResponse" in response.content
    assert b"ProcessDocumentResult" in response.content


def test_notereader_gateway_create_fastapi_router_no_handler():
    """Test WSGI app creation fails without ProcessDocument handler"""
    gateway = NoteReaderService()

    # No handler registered - should raise ValueError
    with pytest.raises(ValueError):
        gateway.create_fastapi_router()


def test_notereader_gateway_get_metadata():
    """Test retrieving gateway metadata"""
    gateway = NoteReaderService()

    # Register a handler to have some capabilities
    @gateway.method("ProcessDocument")
    def process_document(request):
        return CdaResponse(document="processed", error=None)

    # Get metadata
    metadata = gateway.get_metadata()

    # Verify metadata contains expected keys
    assert "service_type" in metadata
    assert metadata["service_type"] in "NoteReaderService"
    assert "operations" in metadata
    assert "ProcessDocument" in metadata["operations"]
    assert "system_type" in metadata
    assert metadata["system_type"] == "EHR_CDA"
    assert "mount_path" in metadata
    assert metadata["mount_path"] == "/notereader"
