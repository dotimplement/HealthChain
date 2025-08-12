"""
Tests for FHIR client external API integration functionality.

Focuses on HTTP operations, authentication, error handling, and response processing.
"""

import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement

from healthchain.gateway.clients.fhir.aio import AsyncFHIRClient
from healthchain.gateway.clients.fhir.base import FHIRAuthConfig


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
        "healthchain.gateway.clients.auth.OAuth2TokenManager"
    ) as mock_manager_class:
        mock_manager = Mock()
        # For sync access during initialization, use a regular Mock
        mock_manager.get_access_token = AsyncMock(return_value="test_token")
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
        "healthchain.gateway.clients.auth.OAuth2TokenManager"
    ) as mock_manager_class:
        mock_manager = Mock()
        # For sync access during initialization, use a regular Mock
        mock_manager.get_access_token = AsyncMock(return_value="test_token")
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_fhir_client_authentication_failure(fhir_client):
    """AsyncFHIRClient handles authentication failures."""
    fhir_client.token_manager.get_access_token.side_effect = Exception("Auth failed")
    with pytest.raises(Exception, match="Auth failed"):
        await fhir_client._get_headers()


@pytest.mark.asyncio
async def test_fhir_client_http_timeout(fhir_client):
    """AsyncFHIRClient handles HTTP timeout errors."""
    with patch.object(fhir_client.client, "get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timed out")
        with pytest.raises(httpx.TimeoutException):
            await fhir_client.read(Patient, "123")
