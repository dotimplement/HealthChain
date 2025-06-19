"""
Tests for FHIR client external API integration functionality.

Focuses on HTTP operations, authentication, error handling, and response processing.
"""

import pytest
import json
import httpx
from unittest.mock import Mock, AsyncMock, patch
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement

from healthchain.gateway.clients.fhir import (
    AsyncFHIRClient,
    FHIRClientError,
)
from healthchain.gateway.clients.auth import FHIRAuthConfig

pytestmark = pytest.mark.anyio


@pytest.fixture
def mock_auth_config():
    """Create a mock FHIR auth configuration."""
    return FHIRAuthConfig(
        base_url="https://test.fhir.org/R4",
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://test.fhir.org/oauth/token",
        scope="system/*.read",
        timeout=30.0,
        verify_ssl=True,
    )


@pytest.fixture
def fhir_client(mock_auth_config):
    """Create a FHIR client for testing."""
    with patch(
        "healthchain.gateway.clients.fhir.OAuth2TokenManager"
    ) as mock_manager_class:
        mock_manager = AsyncMock()
        mock_manager.get_access_token.return_value = "test_token"
        mock_manager_class.return_value = mock_manager

        client = AsyncFHIRClient(auth_config=mock_auth_config)
        client.token_manager = mock_manager
        return client


@pytest.fixture
def fhir_client_with_limits(mock_auth_config):
    """Create an AsyncFHIRClient with connection limits for testing."""
    limits = httpx.Limits(
        max_connections=50,
        max_keepalive_connections=10,
        keepalive_expiry=30.0,
    )
    with patch(
        "healthchain.gateway.clients.fhir.OAuth2TokenManager"
    ) as mock_manager_class:
        mock_manager = AsyncMock()
        mock_manager.get_access_token.return_value = "test_token"
        mock_manager_class.return_value = mock_manager

        client = AsyncFHIRClient(auth_config=mock_auth_config, limits=limits)
        client.token_manager = mock_manager
        return client


@pytest.fixture
def mock_httpx_response():
    """Create a mock httpx response."""
    response = Mock(spec=httpx.Response)
    response.is_success = True
    response.status_code = 200
    response.json.return_value = {"resourceType": "Patient", "id": "123"}
    return response


def test_fhir_client_initialization_and_configuration(mock_auth_config):
    """AsyncFHIRClient initializes with correct configuration and headers."""
    with patch("healthchain.gateway.clients.fhir.OAuth2TokenManager"):
        client = AsyncFHIRClient(auth_config=mock_auth_config)

        # Test configuration
        assert client.base_url == "https://test.fhir.org/R4/"
        assert client.timeout == 30.0
        assert client.verify_ssl is True

        # Test headers
        assert client.base_headers["Accept"] == "application/fhir+json"
        assert client.base_headers["Content-Type"] == "application/fhir+json"


def test_async_fhir_client_conforms_to_protocol(fhir_client):
    """AsyncFHIRClient implements the required protocol methods."""
    # Check that client has all required protocol methods
    assert hasattr(fhir_client, "read")
    assert hasattr(fhir_client, "search")
    assert hasattr(fhir_client, "create")
    assert hasattr(fhir_client, "update")
    assert hasattr(fhir_client, "delete")
    assert hasattr(fhir_client, "transaction")
    assert hasattr(fhir_client, "capabilities")

    # Check that methods are callable
    assert callable(getattr(fhir_client, "read"))
    assert callable(getattr(fhir_client, "search"))


async def test_fhir_client_authentication_and_headers(fhir_client):
    """AsyncFHIRClient manages OAuth tokens and includes proper headers."""
    # Test first call includes token and headers
    headers = await fhir_client._get_headers()
    assert headers["Authorization"] == "Bearer test_token"
    assert headers["Accept"] == "application/fhir+json"
    assert headers["Content-Type"] == "application/fhir+json"

    # Test token refresh on subsequent calls
    await fhir_client._get_headers()
    assert fhir_client.token_manager.get_access_token.call_count == 2


def test_fhir_client_url_building(fhir_client):
    """AsyncFHIRClient builds URLs correctly with and without parameters."""
    # Without parameters
    url = fhir_client._build_url("Patient/123")
    assert url == "https://test.fhir.org/R4/Patient/123"

    # With parameters (None values filtered)
    params = {"name": "John", "active": True, "limit": None}
    url = fhir_client._build_url("Patient", params)
    assert "https://test.fhir.org/R4/Patient?" in url
    assert "name=John" in url
    assert "active=True" in url
    assert "limit" not in url


@pytest.mark.parametrize(
    "status_code,is_success,should_raise",
    [
        (200, True, False),
        (201, True, False),
        (400, False, True),
        (404, False, True),
        (500, False, True),
    ],
)
def test_fhir_client_response_handling(
    fhir_client, status_code, is_success, should_raise
):
    """AsyncFHIRClient handles HTTP status codes and error responses appropriately."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.is_success = is_success
    mock_response.status_code = status_code
    mock_response.json.return_value = {"resourceType": "OperationOutcome"}

    if should_raise:
        with pytest.raises(FHIRClientError) as exc_info:
            fhir_client._handle_response(mock_response)
        assert exc_info.value.status_code == status_code
    else:
        result = fhir_client._handle_response(mock_response)
        assert result == {"resourceType": "OperationOutcome"}


def test_fhir_client_error_extraction_and_invalid_json(fhir_client):
    """AsyncFHIRClient extracts error diagnostics and handles invalid JSON."""
    # Test error extraction from OperationOutcome
    mock_response = Mock(spec=httpx.Response)
    mock_response.is_success = False
    mock_response.status_code = 422
    mock_response.json.return_value = {
        "resourceType": "OperationOutcome",
        "issue": [{"diagnostics": "Validation failed on field X"}],
    }

    with pytest.raises(FHIRClientError) as exc_info:
        fhir_client._handle_response(mock_response)
    assert "Validation failed on field X" in str(exc_info.value)
    assert exc_info.value.status_code == 422

    # Test invalid JSON handling
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
    mock_response.text = "Invalid response text"
    mock_response.status_code = 500

    with pytest.raises(FHIRClientError) as exc_info:
        fhir_client._handle_response(mock_response)
    assert "Invalid JSON response" in str(exc_info.value)


async def test_fhir_client_crud_operations(fhir_client, mock_httpx_response):
    """AsyncFHIRClient performs CRUD operations correctly."""
    # Test READ operation
    with patch.object(
        fhir_client.client, "get", return_value=mock_httpx_response
    ) as mock_get:
        with patch.object(
            fhir_client, "_get_headers", return_value={"Authorization": "Bearer token"}
        ):
            result = await fhir_client.read(Patient, "123")
            mock_get.assert_called_once_with(
                "https://test.fhir.org/R4/Patient/123",
                headers={"Authorization": "Bearer token"},
            )
            assert isinstance(result, Patient)
            assert result.id == "123"

    # Test CREATE operation
    patient = Patient(id="123", active=True)
    mock_httpx_response.json.return_value = {
        "resourceType": "Patient",
        "id": "new-123",
        "active": True,
    }

    with patch.object(
        fhir_client.client, "post", return_value=mock_httpx_response
    ) as mock_post:
        with patch.object(
            fhir_client, "_get_headers", return_value={"Authorization": "Bearer token"}
        ):
            result = await fhir_client.create(patient)
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://test.fhir.org/R4/Patient"
            assert "content" in call_args[1]
            assert isinstance(result, Patient)
            assert result.id == "new-123"

    # Test DELETE operation
    mock_delete_response = Mock(spec=httpx.Response)
    mock_delete_response.is_success = True
    mock_delete_response.status_code = 204

    with patch.object(
        fhir_client.client, "delete", return_value=mock_delete_response
    ) as mock_delete:
        with patch.object(fhir_client, "_get_headers", return_value={}):
            result = await fhir_client.delete(Patient, "123")
            mock_delete.assert_called_once_with(
                "https://test.fhir.org/R4/Patient/123", headers={}
            )
            assert result is True


async def test_fhir_client_search_and_capabilities(fhir_client):
    """AsyncFHIRClient handles search operations and server capabilities."""
    # Test SEARCH operation
    bundle_response = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [{"resource": {"resourceType": "Patient", "id": "123"}}],
    }
    mock_response = Mock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.json.return_value = bundle_response

    with patch.object(
        fhir_client.client, "get", return_value=mock_response
    ) as mock_get:
        with patch.object(fhir_client, "_get_headers", return_value={}):
            params = {"name": "John", "active": True}
            result = await fhir_client.search(Patient, params)

            call_url = mock_get.call_args[0][0]
            assert "Patient?" in call_url
            assert "name=John" in call_url
            assert "active=True" in call_url
            assert isinstance(result, Bundle)
            assert result.type == "searchset"

    # Test CAPABILITIES operation
    capabilities_response = {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "date": "2023-01-01T00:00:00Z",
        "format": ["json"],
    }
    mock_response.json.return_value = capabilities_response

    with patch.object(
        fhir_client.client, "get", return_value=mock_response
    ) as mock_get:
        with patch.object(fhir_client, "_get_headers", return_value={}):
            result = await fhir_client.capabilities()
            mock_get.assert_called_once_with(
                "https://test.fhir.org/R4/metadata", headers={}
            )
            assert isinstance(result, CapabilityStatement)
            assert result.status == "active"


def test_fhir_client_resource_type_resolution(fhir_client):
    """AsyncFHIRClient resolves resource types from classes, strings, and handles errors."""
    # Test with FHIR resource class
    type_name, resource_class = fhir_client._resolve_resource_type(Patient)
    assert type_name == "Patient"
    assert resource_class == Patient

    # Test with string name
    with patch("builtins.__import__") as mock_import:
        mock_module = Mock()
        mock_module.Patient = Patient
        mock_import.return_value = mock_module

        type_name, resource_class = fhir_client._resolve_resource_type("Patient")
        assert type_name == "Patient"
        assert resource_class == Patient
        mock_import.assert_called_once_with(
            "fhir.resources.patient", fromlist=["Patient"]
        )

    # Test invalid resource type
    with pytest.raises(ModuleNotFoundError, match="No module named"):
        fhir_client._resolve_resource_type("InvalidResource")


async def test_fhir_client_authentication_failure(fhir_client):
    """AsyncFHIRClient handles authentication failures."""
    fhir_client.token_manager.get_access_token.side_effect = Exception("Auth failed")
    with pytest.raises(Exception, match="Auth failed"):
        await fhir_client._get_headers()


async def test_fhir_client_http_timeout(fhir_client):
    """AsyncFHIRClient handles HTTP timeout errors."""
    with patch.object(fhir_client.client, "get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timed out")
        with pytest.raises(httpx.TimeoutException):
            await fhir_client.read(Patient, "123")


def test_fhir_client_error_class():
    """FHIRClientError preserves response data for debugging."""
    response_data = {"resourceType": "OperationOutcome", "issue": []}
    error = FHIRClientError("Test error", status_code=400, response_data=response_data)

    assert error.status_code == 400
    assert error.response_data == response_data
    assert str(error) == "Test error"
