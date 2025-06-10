"""
Tests for the FHIR client module in the HealthChain gateway system.

This module tests FHIR client interfaces and HTTP request handling functionality.
Auth-related tests are in test_auth.py.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, Mock

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
def mock_fhir_response():
    """Create a mock FHIR resource response."""
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


class TestAsyncFHIRClient:
    """Test AsyncFHIRClient functionality."""

    def test_client_initialization(self, fhir_client, fhir_auth_config):
        """Test FHIR client initializes correctly."""
        assert fhir_client.base_url == "https://example.com/fhir/R4/"
        assert fhir_client.timeout == 30
        assert fhir_client.verify_ssl is True
        assert isinstance(fhir_client.token_manager, OAuth2TokenManager)

    async def test_client_context_manager(self, fhir_client):
        """Test FHIR client as async context manager."""
        async with fhir_client as client:
            assert client is fhir_client

    def test_build_url(self, fhir_client):
        """Test URL building functionality."""
        # Test without parameters
        url = fhir_client._build_url("Patient/123")
        assert url == "https://example.com/fhir/R4/Patient/123"

        # Test with parameters
        url = fhir_client._build_url("Patient", {"name": "John", "gender": "male"})
        assert "name=John" in url
        assert "gender=male" in url

    @patch.object(OAuth2TokenManager, "get_access_token")
    async def test_get_headers(self, mock_get_token, fhir_client):
        """Test header generation with OAuth2 token."""
        mock_get_token.return_value = "test_access_token"

        headers = await fhir_client._get_headers()

        assert headers["Authorization"] == "Bearer test_access_token"
        assert headers["Accept"] == "application/fhir+json"
        assert headers["Content-Type"] == "application/fhir+json"

    def test_handle_response_success(self, fhir_client, mock_fhir_response):
        """Test successful response handling."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.json.return_value = mock_fhir_response
        mock_response.is_success = True

        result = fhir_client._handle_response(mock_response)
        assert result == mock_fhir_response

    def test_handle_response_http_error(self, fhir_client):
        """Test HTTP error response handling."""
        from unittest.mock import Mock

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

    def test_handle_response_invalid_json(self, fhir_client):
        """Test response with invalid JSON."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid response"
        mock_response.status_code = 500

        with pytest.raises(FHIRClientError, match="Invalid JSON response"):
            fhir_client._handle_response(mock_response)

    @patch("httpx.AsyncClient.get")
    @patch.object(OAuth2TokenManager, "get_access_token")
    async def test_capabilities(
        self, mock_get_token, mock_get, fhir_client, mock_capability_response
    ):
        """Test fetching server capabilities."""
        mock_get_token.return_value = "test_token"

        # Mock successful response
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
    async def test_read_resource(
        self, mock_get_token, mock_get, fhir_client, mock_fhir_response
    ):
        """Test reading a FHIR resource."""
        from fhir.resources.patient import Patient

        mock_get_token.return_value = "test_token"

        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = mock_fhir_response
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
    async def test_search_resources(self, mock_get_token, mock_get, fhir_client):
        """Test searching for FHIR resources."""
        mock_get_token.return_value = "test_token"

        # Mock Bundle response
        bundle_response = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 1,
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "test-patient-id"}}
            ],
        }

        mock_response = Mock()
        mock_response.json.return_value = bundle_response
        mock_response.is_success = True
        mock_get.return_value = mock_response

        result = await fhir_client.search("Patient", {"name": "John"})

        assert result.__resource_type__ == "Bundle"
        assert result.type == "searchset"
        assert result.total == 1
        assert len(result.entry) == 1
        mock_get.assert_called_once()

    async def test_close_client(self, fhir_client):
        """Test closing the HTTP client."""
        # Mock the httpx client close method
        fhir_client.client.aclose = AsyncMock()

        await fhir_client.close()

        fhir_client.client.aclose.assert_called_once()
