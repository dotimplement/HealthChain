"""
Tests for the FHIR client module in the HealthChain gateway system.

This module tests FHIR client interfaces and HTTP request handling functionality.
Auth-related tests are in test_auth.py.
"""

import pytest
import json
import httpx
from unittest.mock import AsyncMock, Mock, patch

from healthchain.gateway.clients import (
    AsyncFHIRClient,
    OAuth2TokenManager,
    FHIRAuthConfig,
)
from healthchain.gateway.clients.fhir import FHIRClientError

# Configure pytest-anyio for async tests
pytestmark = pytest.mark.anyio


@pytest.fixture
def fhir_auth_config():
    """Create a FHIR authentication configuration for testing."""
    return FHIRAuthConfig(
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://example.com/oauth/token",
        base_url="https://example.com/fhir/R4",
        scope="system/*.read system/*.write",
        audience="https://example.com/fhir",
    )


@pytest.fixture
def fhir_client(fhir_auth_config):
    """Create an AsyncFHIRClient for testing."""
    return AsyncFHIRClient(auth_config=fhir_auth_config)


@pytest.fixture
def fhir_client_with_limits(fhir_auth_config):
    """Create an AsyncFHIRClient with connection limits for testing."""
    limits = httpx.Limits(
        max_connections=50,
        max_keepalive_connections=10,
        keepalive_expiry=30.0,
    )
    return AsyncFHIRClient(auth_config=fhir_auth_config, limits=limits)


@pytest.fixture
def mock_patient_response():
    """Create a mock FHIR Patient resource response."""
    return {
        "resourceType": "Patient",
        "id": "test-patient-id",
        "name": [{"family": "Doe", "given": ["John"]}],
        "gender": "male",
    }


@pytest.fixture
def mock_capability_response():
    """Create a mock CapabilityStatement response."""
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": "2023-01-01T00:00:00Z",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
    }


@pytest.fixture
def mock_bundle_response():
    """Create a mock Bundle response for search operations."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 1,
        "entry": [{"resource": {"resourceType": "Patient", "id": "test-patient-id"}}],
    }


def test_async_fhir_client_initialization_with_basic_config(fhir_client):
    """Test AsyncFHIRClient initializes correctly with basic configuration."""
    assert fhir_client.base_url == "https://example.com/fhir/R4/"
    assert fhir_client.timeout == 30
    assert fhir_client.verify_ssl is True
    assert isinstance(fhir_client.token_manager, OAuth2TokenManager)


def test_async_fhir_client_initialization_with_connection_limits(
    fhir_client_with_limits,
):
    """Test AsyncFHIRClient properly configures httpx connection pooling limits."""
    # Access connection pool limits through the transport layer
    pool = fhir_client_with_limits.client._transport._pool
    assert pool._max_connections == 50
    assert pool._max_keepalive_connections == 10
    assert pool._keepalive_expiry == 30.0


def test_async_fhir_client_url_building_without_parameters(fhir_client):
    """Test URL construction for resource paths without query parameters."""
    url = fhir_client._build_url("Patient/123")
    assert url == "https://example.com/fhir/R4/Patient/123"


def test_async_fhir_client_url_building_with_parameters(fhir_client):
    """Test URL construction includes query parameters correctly."""
    url = fhir_client._build_url("Patient", {"name": "John", "gender": "male"})
    assert "name=John" in url
    assert "gender=male" in url


@patch.object(OAuth2TokenManager, "get_access_token")
async def test_async_fhir_client_header_generation_with_oauth_token(
    mock_get_token, fhir_client
):
    """Test that request headers include OAuth2 Bearer token and FHIR content types."""
    mock_get_token.return_value = "test_access_token"

    headers = await fhir_client._get_headers()

    assert headers["Authorization"] == "Bearer test_access_token"
    assert headers["Accept"] == "application/fhir+json"
    assert headers["Content-Type"] == "application/fhir+json"


def test_async_fhir_client_successful_response_handling(
    fhir_client, mock_patient_response
):
    """Test that successful HTTP responses are properly parsed and returned."""
    mock_response = Mock()
    mock_response.json.return_value = mock_patient_response
    mock_response.is_success = True

    result = fhir_client._handle_response(mock_response)
    assert result == mock_patient_response


def test_async_fhir_client_http_error_response_handling(fhir_client):
    """Test that HTTP errors are converted to FHIRClientError with proper context."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "resourceType": "OperationOutcome",
        "issue": [{"diagnostics": "Resource not found"}],
    }
    mock_response.is_success = False
    mock_response.status_code = 404

    with pytest.raises(FHIRClientError) as exc_info:
        fhir_client._handle_response(mock_response)

    assert exc_info.value.status_code == 404
    assert "FHIR request failed: 404" in str(exc_info.value)


def test_async_fhir_client_invalid_json_response_handling(fhir_client):
    """Test that malformed JSON responses raise appropriate errors."""
    mock_response = Mock()
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.text = "Invalid response"
    mock_response.status_code = 500

    with pytest.raises(FHIRClientError, match="Invalid JSON response"):
        fhir_client._handle_response(mock_response)


@patch("httpx.AsyncClient.get")
@patch.object(OAuth2TokenManager, "get_access_token")
async def test_async_fhir_client_capabilities_endpoint_integration(
    mock_get_token, mock_get, fhir_client, mock_capability_response
):
    """Test fetching server CapabilityStatement and parsing into FHIR resource."""
    mock_get_token.return_value = "test_token"
    mock_response = Mock()
    mock_response.json.return_value = mock_capability_response
    mock_response.is_success = True
    mock_get.return_value = mock_response

    result = await fhir_client.capabilities()

    assert result.__resource_type__ == "CapabilityStatement"
    assert result.status == "active"
    assert result.kind == "instance"
    mock_get.assert_called_once()


@patch("httpx.AsyncClient.get")
@patch.object(OAuth2TokenManager, "get_access_token")
async def test_async_fhir_client_read_resource_by_id(
    mock_get_token, mock_get, fhir_client, mock_patient_response
):
    """Test reading a specific FHIR resource by ID and type."""
    from fhir.resources.patient import Patient

    mock_get_token.return_value = "test_token"
    mock_response = Mock()
    mock_response.json.return_value = mock_patient_response
    mock_response.is_success = True
    mock_get.return_value = mock_response

    result = await fhir_client.read("Patient", "test-patient-id")

    assert isinstance(result, Patient)
    assert result.__resource_type__ == "Patient"
    assert result.id == "test-patient-id"
    assert result.gender == "male"
    mock_get.assert_called_once()


@patch("httpx.AsyncClient.get")
@patch.object(OAuth2TokenManager, "get_access_token")
async def test_async_fhir_client_search_resources_with_parameters(
    mock_get_token, mock_get, fhir_client, mock_bundle_response
):
    """Test searching for FHIR resources with query parameters returns Bundle."""
    mock_get_token.return_value = "test_token"
    mock_response = Mock()
    mock_response.json.return_value = mock_bundle_response
    mock_response.is_success = True
    mock_get.return_value = mock_response

    result = await fhir_client.search("Patient", {"name": "John"})

    assert result.__resource_type__ == "Bundle"
    assert result.type == "searchset"
    assert result.total == 1
    assert len(result.entry) == 1
    mock_get.assert_called_once()


async def test_async_fhir_client_context_manager_lifecycle(fhir_client):
    """Test AsyncFHIRClient properly supports async context manager protocol."""
    async with fhir_client as client:
        assert client is fhir_client


async def test_async_fhir_client_cleanup_on_close(fhir_client):
    """Test that closing the client properly cleans up HTTP connections."""
    fhir_client.client.aclose = AsyncMock()
    await fhir_client.close()
    fhir_client.client.aclose.assert_called_once()
