"""
Tests for FHIR client external API integration functionality.

Focuses on HTTP operations, authentication, error handling, and response processing.
"""

import pytest
import httpx
from unittest.mock import Mock, patch
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement

from healthchain.gateway.clients.fhir.sync import FHIRClient
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
        mock_manager.get_access_token = Mock(return_value="test_token")
        mock_manager_class.return_value = mock_manager

        client = FHIRClient(auth_config=mock_auth_config)
        client.token_manager = mock_manager
        return client


@pytest.fixture
def fhir_client_with_limits(mock_auth_config):
    """Create an FHIRClient with connection limits for testing."""
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
        mock_manager.get_access_token = Mock(return_value="test_token")
        mock_manager_class.return_value = mock_manager

        client = FHIRClient(auth_config=mock_auth_config, limits=limits)
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


def test_fhir_client_authentication_and_headers(fhir_client):
    """FHIRClient manages OAuth tokens and includes proper headers."""
    # Test first call includes token and headers
    headers = fhir_client._get_headers()
    assert headers["Authorization"] == "Bearer test_token"
    assert headers["Accept"] == "application/fhir+json"
    assert headers["Content-Type"] == "application/fhir+json"

    # Test token refresh on subsequent calls
    fhir_client._get_headers()
    assert fhir_client.token_manager.get_access_token.call_count == 2


def test_fhir_client_crud_operations(fhir_client, mock_httpx_response):
    """FHIRClient performs CRUD operations correctly."""
    # Test READ operation
    with patch.object(
        fhir_client.client, "get", return_value=mock_httpx_response
    ) as mock_get:
        with patch.object(
            fhir_client, "_get_headers", return_value={"Authorization": "Bearer token"}
        ):
            result = fhir_client.read(Patient, "123")
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
            result = fhir_client.create(patient)
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
            result = fhir_client.delete(Patient, "123")
            mock_delete.assert_called_once_with(
                "https://test.fhir.org/R4/Patient/123", headers={}
            )
            assert result is True


def test_fhir_client_search_and_capabilities(fhir_client):
    """FHIRClient handles search operations and server capabilities."""
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
            result = fhir_client.search(Patient, params)

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
            result = fhir_client.capabilities()
            mock_get.assert_called_once_with(
                "https://test.fhir.org/R4/metadata", headers={}
            )
            assert isinstance(result, CapabilityStatement)
            assert result.status == "active"


def test_fhir_client_authentication_failure(fhir_client):
    """FHIRClient handles authentication failures."""
    fhir_client.token_manager.get_access_token.side_effect = Exception("Auth failed")
    with pytest.raises(Exception, match="Auth failed"):
        fhir_client._get_headers()


def test_fhir_client_http_timeout(fhir_client):
    """FHIRClient handles HTTP timeout errors."""
    with patch.object(fhir_client.client, "get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timed out")
        with pytest.raises(httpx.TimeoutException):
            fhir_client.read(Patient, "123")


def test_fhir_client_context_manager_lifecycle(mock_auth_config):
    """FHIRClient context manager properly opens and closes connections."""
    with patch("healthchain.gateway.clients.auth.OAuth2TokenManager"):
        # Test context manager entry and exit
        with FHIRClient(auth_config=mock_auth_config) as client:
            assert client.client is not None
            assert hasattr(client, "close")

            # Mock the close method to verify it gets called
            client.close = Mock()

        # Verify close was called on exit
        client.close.assert_called_once()


def test_fhir_client_context_manager_handles_exceptions(mock_auth_config):
    """FHIRClient context manager properly closes connections even when exceptions occur."""
    with patch("healthchain.gateway.clients.auth.OAuth2TokenManager"):
        try:
            with FHIRClient(auth_config=mock_auth_config) as client:
                client.close = Mock()
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify close was still called despite the exception
        client.close.assert_called_once()


def test_fhir_client_manual_close_method(mock_auth_config):
    """FHIRClient close method properly shuts down HTTP client."""
    with patch("healthchain.gateway.clients.auth.OAuth2TokenManager"):
        client = FHIRClient(auth_config=mock_auth_config)

        # Mock the httpx client
        client.client = Mock()
        client.client.close = Mock()

        # Test manual close
        client.close()

        # Verify httpx client close was called
        client.client.close.assert_called_once()
