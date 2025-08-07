"""
Shared test fixtures and data for gateway tests.
This could be used to reduce duplication across test files.
"""

import pytest
from unittest.mock import Mock
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle
from healthchain.gateway.clients.fhir.base import FHIRAuthConfig


# =============================================================================
# FHIR Test Data
# =============================================================================


@pytest.fixture
def sample_patient():
    """Standard test patient used across multiple test files."""
    return Patient(
        id="test-patient-123",
        active=True,
        name=[{"family": "TestFamily", "given": ["TestGiven"]}],
        gender="unknown",
    )


@pytest.fixture
def sample_patient_data():
    """Raw patient data for JSON responses."""
    return {
        "resourceType": "Patient",
        "id": "test-patient-123",
        "active": True,
        "name": [{"family": "TestFamily", "given": ["TestGiven"]}],
        "gender": "unknown",
    }


@pytest.fixture
def sample_bundle():
    """Standard test bundle for transaction testing."""
    return Bundle(
        type="transaction",
        entry=[
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "test-patient-123",
                    "active": True,
                },
                "request": {"method": "PUT", "url": "Patient/test-patient-123"},
            }
        ],
    )


# =============================================================================
# Connection & Auth Test Data
# =============================================================================


@pytest.fixture
def standard_auth_config():
    """Standard FHIR auth config used across tests."""
    return FHIRAuthConfig(
        base_url="https://test.fhir.org/R4",
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://test.fhir.org/oauth/token",
        scope="system/*.read",
    )


@pytest.fixture
def standard_connection_string():
    """Standard FHIR connection string for testing."""
    return (
        "fhir://test.fhir.org/R4?"
        "client_id=test_client&"
        "client_secret=test_secret&"
        "token_url=https://test.fhir.org/oauth/token&"
        "scope=system/*.read"
    )


@pytest.fixture
def multi_source_connection_strings():
    """Multiple connection strings for multi-source testing."""
    return {
        "source1": (
            "fhir://source1.fhir.org/R4?"
            "client_id=client1&client_secret=secret1&"
            "token_url=https://source1.fhir.org/token"
        ),
        "source2": (
            "fhir://source2.fhir.org/R4?"
            "client_id=client2&client_secret=secret2&"
            "token_url=https://source2.fhir.org/token"
        ),
    }


# =============================================================================
# Mock HTTP Responses
# =============================================================================


@pytest.fixture
def mock_successful_patient_response():
    """Mock HTTP response for successful patient read."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "resourceType": "Patient",
        "id": "test-patient-123",
        "active": True,
    }
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def mock_token_response():
    """Mock HTTP response for OAuth token endpoint."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def mock_token_data():
    """Raw token data for JSON responses."""
    return {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


# =============================================================================
# Common Test Utilities
# =============================================================================


def create_mock_client(async_mode=False):
    """Create a standard mock FHIR client."""
    mock_client = Mock()

    if async_mode:
        from unittest.mock import AsyncMock

        mock_client.read = AsyncMock(return_value=Patient(id="test", active=True))
        mock_client.create = AsyncMock(return_value=Patient(id="test", active=True))
        mock_client.update = AsyncMock(return_value=Patient(id="test", active=True))
        mock_client.delete = AsyncMock()
        mock_client.search = AsyncMock(return_value=Bundle(type="searchset", entry=[]))
        mock_client.close = AsyncMock()
    else:
        mock_client.read.return_value = Patient(id="test", active=True)
        mock_client.create.return_value = Patient(id="test", active=True)
        mock_client.update.return_value = Patient(id="test", active=True)
        mock_client.delete.return_value = None
        mock_client.search.return_value = Bundle(type="searchset", entry=[])
        mock_client.close = Mock()

    return mock_client


def create_mock_connection_manager(async_mode=False):
    """Create a standard mock connection manager."""
    mock_manager = Mock()
    mock_client = create_mock_client(async_mode)
    mock_manager.get_client.return_value = mock_client
    mock_manager.add_source = Mock()

    if async_mode:
        from unittest.mock import AsyncMock

        mock_manager.close = AsyncMock()

    return mock_manager


# =============================================================================
# Error Test Data
# =============================================================================


@pytest.fixture
def invalid_connection_strings():
    """Collection of invalid connection strings for error testing."""
    return [
        "invalid://not-fhir",
        "fhir://",  # Missing hostname
        "fhir://example.com",  # Missing required params
        "not-a-url-at-all",
        "http://wrong-scheme.com/fhir",
    ]


@pytest.fixture
def http_error_scenarios():
    """Common HTTP error scenarios for testing."""
    import httpx

    return {
        "timeout": httpx.ConnectTimeout("Connection timed out"),
        "404": httpx.HTTPStatusError(
            "Not found", request=Mock(), response=Mock(status_code=404)
        ),
        "500": httpx.HTTPStatusError(
            "Server error", request=Mock(), response=Mock(status_code=500)
        ),
        "401": httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=Mock(status_code=401)
        ),
    }
