import pytest
from unittest.mock import patch, MagicMock

from healthchain.gateway.services.notereader import (
    NoteReaderService,
    NoteReaderAdapter,
    NoteReaderConfig,
)
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse


def test_notereader_adapter_initialization():
    """Test NoteReaderAdapter initialization with default config"""
    adapter = NoteReaderAdapter()
    assert isinstance(adapter.config, NoteReaderConfig)
    assert adapter.config.service_name == "ICDSServices"
    assert adapter.config.namespace == "urn:epic-com:Common.2013.Services"
    assert adapter.config.system_type == "EHR_CDA"


def test_notereader_adapter_create():
    """Test NoteReaderAdapter.create factory method"""
    adapter = NoteReaderAdapter.create()
    assert isinstance(adapter, NoteReaderAdapter)
    assert isinstance(adapter.config, NoteReaderConfig)


def test_notereader_adapter_register_handler():
    """Test handler registration with adapter"""
    adapter = NoteReaderAdapter()
    mock_handler = MagicMock(return_value=CdaResponse(document="test", error=None))

    # Register handler
    adapter.register_handler("ProcessDocument", mock_handler)

    # Verify handler is registered
    assert "ProcessDocument" in adapter._handlers
    assert adapter._handlers["ProcessDocument"] == mock_handler


def test_notereader_service_initialization():
    """Test NoteReaderService initialization"""
    service = NoteReaderService()
    assert isinstance(service.adapter, NoteReaderAdapter)


def test_notereader_service_method_decorator():
    """Test method decorator for registering handlers"""
    service = NoteReaderService()

    @service.method("ProcessDocument")
    def process_document(request):
        return CdaResponse(document="processed", error=None)

    # Verify handler is registered with adapter
    assert "ProcessDocument" in service.adapter._handlers


def test_notereader_adapter_extract_request():
    """Test request extraction from parameters"""
    adapter = NoteReaderAdapter()

    # Case 1: CdaRequest passed directly
    request = CdaRequest(document="<doc>test</doc>")
    extracted = adapter._extract_request("ProcessDocument", {"request": request})
    assert extracted == request

    # Case 2: CdaRequest as single parameter
    extracted = adapter._extract_request("ProcessDocument", {"param": request})
    assert extracted == request

    # Case 3: Build from params
    adapter.register_handler("ProcessDocument", lambda x: x)
    extracted = adapter._extract_request(
        "ProcessDocument", {"document": "<doc>test</doc>"}
    )
    assert isinstance(extracted, CdaRequest)
    assert extracted.document == "<doc>test</doc>"


@patch("healthchain.gateway.services.notereader.WsgiApplication")
def test_notereader_service_create_wsgi_app(mock_wsgi):
    """Test WSGI app creation for SOAP service"""
    service = NoteReaderService()

    # Register required ProcessDocument handler
    @service.method("ProcessDocument")
    def process_document(request):
        return CdaResponse(document="processed", error=None)

    # Create WSGI app
    wsgi_app = service.create_wsgi_app()
    mock_wsgi.assert_called_once()

    # Verify WSGI app was created
    assert wsgi_app is not None

    # Verify we can get the default mount path from config
    config = service.adapter.config
    assert hasattr(config, "default_mount_path")
    assert config.default_mount_path == "/notereader"


def test_notereader_service_create_wsgi_app_no_handler():
    """Test WSGI app creation fails without ProcessDocument handler"""
    service = NoteReaderService()

    # No handler registered - should raise ValueError
    with pytest.raises(ValueError):
        service.create_wsgi_app()
