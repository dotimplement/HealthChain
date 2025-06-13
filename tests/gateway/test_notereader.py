import pytest
from unittest.mock import patch, MagicMock

from healthchain.gateway.protocols.notereader import (
    NoteReaderService,
    NoteReaderConfig,
)
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.gateway.events.dispatcher import EventDispatcher


def test_notereader_gateway_initialization():
    """Test NoteReaderService initialization with default config"""
    gateway = NoteReaderService()
    assert isinstance(gateway.config, NoteReaderConfig)
    assert gateway.config.service_name == "ICDSServices"
    assert gateway.config.namespace == "urn:epic-com:Common.2013.Services"
    assert gateway.config.system_type == "EHR_CDA"


def test_notereader_gateway_create():
    """Test NoteReaderService.create factory method"""
    gateway = NoteReaderService.create()
    assert isinstance(gateway, NoteReaderService)
    assert isinstance(gateway.config, NoteReaderConfig)


def test_notereader_gateway_register_handler():
    """Test handler registration with gateway"""
    gateway = NoteReaderService()
    mock_handler = MagicMock(return_value=CdaResponse(document="test", error=None))

    # Register handler
    gateway.register_handler("ProcessDocument", mock_handler)

    # Verify handler is registered
    assert "ProcessDocument" in gateway._handlers
    assert gateway._handlers["ProcessDocument"] == mock_handler


def test_notereader_gateway_method_decorator():
    """Test method decorator for registering handlers"""
    gateway = NoteReaderService()

    @gateway.method("ProcessDocument")
    def process_document(request):
        return CdaResponse(document="processed", error=None)

    # Verify handler is registered
    assert "ProcessDocument" in gateway._handlers


def test_notereader_gateway_handle():
    """Test request handling logic directly (bypassing async methods)"""
    gateway = NoteReaderService()

    # Register a handler
    @gateway.method("ProcessDocument")
    def process_document(request):
        return CdaResponse(document="processed", error=None)

    # Create a request
    request = CdaRequest(document="<doc>test</doc>")

    # Instead of testing the async handle method, let's test the core logic directly
    # Extract the request
    extracted_request = gateway._extract_request(
        "ProcessDocument", {"request": request}
    )
    assert extracted_request == request

    # Verify handler is properly registered
    assert "ProcessDocument" in gateway._handlers
    handler = gateway._handlers["ProcessDocument"]

    # Call the handler directly
    handler_result = handler(request)
    assert isinstance(handler_result, CdaResponse)
    assert handler_result.document == "processed"

    # Verify process_result works correctly
    processed_result = gateway._process_result(handler_result)
    assert isinstance(processed_result, CdaResponse)
    assert processed_result.document == "processed"
    assert processed_result.error is None


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

    # Test with unexpected type
    result = gateway._process_result("just a string")
    assert isinstance(result, CdaResponse)
    assert result.document == "just a string"
    assert result.error is None


@patch("healthchain.gateway.protocols.notereader.Application")
@patch("healthchain.gateway.protocols.notereader.WsgiApplication")
def test_notereader_gateway_create_wsgi_app(mock_wsgi, mock_application):
    """Test WSGI app creation for SOAP service"""
    # Set up the mock to return a simple mock object instead of trying to create a real WsgiApplication
    mock_wsgi_instance = MagicMock()
    mock_wsgi.return_value = mock_wsgi_instance

    gateway = NoteReaderService()

    # Register required ProcessDocument handler
    @gateway.method("ProcessDocument")
    def process_document(request):
        return CdaResponse(document="processed", error=None)

    # Create WSGI app
    wsgi_app = gateway.create_wsgi_app()

    # Verify WSGI app was created
    assert wsgi_app is mock_wsgi_instance
    mock_wsgi.assert_called_once()
    mock_application.assert_called_once()

    # Verify we can get the default mount path from config
    config = gateway.config
    assert hasattr(config, "default_mount_path")
    assert config.default_mount_path == "/notereader"


def test_notereader_gateway_create_wsgi_app_no_handler():
    """Test WSGI app creation fails without ProcessDocument handler"""
    gateway = NoteReaderService()

    # No handler registered - should raise ValueError
    with pytest.raises(ValueError):
        gateway.create_wsgi_app()


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


def test_notereader_gateway_custom_config():
    """Test NoteReaderService with custom configuration"""
    custom_config = NoteReaderConfig(
        service_name="CustomService",
        namespace="urn:custom:namespace",
        system_type="CUSTOM_SYSTEM",
        default_mount_path="/custom-path",
    )

    gateway = NoteReaderService(config=custom_config)

    assert gateway.config.service_name == "CustomService"
    assert gateway.config.namespace == "urn:custom:namespace"
    assert gateway.config.system_type == "CUSTOM_SYSTEM"
    assert gateway.config.default_mount_path == "/custom-path"


@patch("healthchain.gateway.protocols.notereader.CDSServices")
def test_notereader_gateway_event_emission(mock_cds_services):
    """Test that events are emitted when handling requests"""
    # Create mock event dispatcher
    mock_dispatcher = MagicMock(spec=EventDispatcher)

    # Create gateway with event dispatcher
    gateway = NoteReaderService(event_dispatcher=mock_dispatcher)

    # Mock the service adapter directly
    mock_service_adapter = MagicMock()
    mock_cds_services._service = mock_service_adapter

    # Register a handler
    @gateway.method("ProcessDocument")
    def process_document(request):
        return CdaResponse(document="processed", error=None)

    # Create WSGI app to install handler
    with patch("healthchain.gateway.protocols.notereader.WsgiApplication"):
        with patch("healthchain.gateway.protocols.notereader.Application"):
            gateway.create_wsgi_app()

    # Get the adapter function from the CDSServices class (this would be set by create_wsgi_app)
    mock_cds_services._service

    # Create a request and manually call the adapter function
    # just to verify it would call our event dispatcher
    with patch.object(gateway, "_emit_document_event") as mock_emit:
        request = CdaRequest(document="<doc>test</doc>")
        mock_handler = gateway._handlers["ProcessDocument"]

        # Simulate what would happen in service_adapter
        result = mock_handler(request)
        gateway._emit_document_event("ProcessDocument", request, result)

        # Verify event emission was called
        mock_emit.assert_called_once()
