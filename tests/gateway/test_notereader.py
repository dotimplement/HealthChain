import pytest
from unittest.mock import patch, MagicMock

from healthchain.gateway.soap.notereader import (
    NoteReaderService,
    NoteReaderConfig,
)
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse


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


@patch("healthchain.gateway.soap.notereader.Application")
@patch("healthchain.gateway.soap.notereader.WsgiApplication")
def test_notereader_gateway_create_wsgi_app(mock_wsgi, mock_application):
    """Test WSGI app creation for SOAP service"""
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
