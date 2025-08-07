"""
Tests for shared FHIR client functionality in the HealthChain gateway system.

This module tests shared initialization, validation, and utility logic that should work
identically across sync and async FHIR client implementations.
"""

import pytest
import json
import httpx
from unittest.mock import Mock, patch
from fhir.resources.patient import Patient

from healthchain.gateway.clients.fhir.sync import FHIRClient
from healthchain.gateway.clients.fhir.aio import AsyncFHIRClient
from healthchain.gateway.clients.fhir.base import FHIRClientError
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


@pytest.fixture(params=["sync", "async"])
def fhir_client(request, mock_auth_config):
    """Fixture providing both sync and async FHIR clients."""
    if request.param == "sync":
        with patch(
            "healthchain.gateway.clients.auth.OAuth2TokenManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_access_token = Mock(return_value="test_token")
            mock_manager_class.return_value = mock_manager

            client = FHIRClient(auth_config=mock_auth_config)
            client.token_manager = mock_manager
            return client
    else:
        with patch(
            "healthchain.gateway.clients.auth.OAuth2TokenManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_access_token = Mock(return_value="test_token")
            mock_manager_class.return_value = mock_manager

            client = AsyncFHIRClient(auth_config=mock_auth_config)
            client.token_manager = mock_manager
            return client


class TestSharedFHIRClientInitialization:
    """Test FHIR client initialization that should be identical across sync/async implementations."""

    def test_fhir_client_initialization_and_configuration(self, mock_auth_config):
        """FHIR clients initialize with correct configuration and headers."""
        with patch("healthchain.gateway.clients.auth.OAuth2TokenManager"):
            # Test sync client
            sync_client = FHIRClient(auth_config=mock_auth_config)
            assert sync_client.base_url == "https://test.fhir.org/R4/"
            assert sync_client.timeout == 30.0
            assert sync_client.verify_ssl is True
            assert sync_client.base_headers["Accept"] == "application/fhir+json"
            assert sync_client.base_headers["Content-Type"] == "application/fhir+json"

            # Test async client
            async_client = AsyncFHIRClient(auth_config=mock_auth_config)
            assert async_client.base_url == "https://test.fhir.org/R4/"
            assert async_client.timeout == 30.0
            assert async_client.verify_ssl is True
            assert async_client.base_headers["Accept"] == "application/fhir+json"
            assert async_client.base_headers["Content-Type"] == "application/fhir+json"

    def test_fhir_client_conforms_to_protocol(self, fhir_client):
        """FHIR clients implement the required protocol methods."""
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


def test_fhir_client_url_building(fhir_client):
    """FHIR clients build URLs correctly with and without parameters."""
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


def test_fhir_client_resource_type_resolution(fhir_client):
    """FHIR clients resolve resource types from classes, strings, and handle errors."""
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
    """FHIR clients handle HTTP status codes and error responses appropriately."""
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
    """FHIR clients extract error diagnostics and handle invalid JSON."""
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


def test_fhir_client_error_class():
    """FHIRClientError preserves response data for debugging."""
    response_data = {"resourceType": "OperationOutcome", "issue": []}
    error = FHIRClientError("Test error", status_code=400, response_data=response_data)

    assert error.status_code == 400
    assert error.response_data == response_data
    assert str(error) == "Test error"
