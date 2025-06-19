"""
Tests for the FHIR connection manager in the HealthChain gateway system.

This module tests centralized connection management for FHIR sources:
- Connection string parsing and validation
- Source lifecycle management
- Client pooling and retrieval
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from healthchain.gateway.core.connection import FHIRConnectionManager
from healthchain.gateway.core.errors import FHIRConnectionError
from healthchain.gateway.clients.fhir import FHIRServerInterface

# Configure pytest-anyio for async tests
pytestmark = pytest.mark.anyio


@pytest.fixture
def connection_manager():
    """Create a connection manager for testing."""
    return FHIRConnectionManager(
        max_connections=50, max_keepalive_connections=10, keepalive_expiry=30.0
    )


@pytest.fixture
def mock_fhir_client():
    """Create a mock FHIR client for testing."""
    client = Mock(spec=FHIRServerInterface)
    client.base_url = "https://test.fhir.com/R4"
    return client


@pytest.mark.parametrize(
    "connection_string,should_succeed",
    [
        # Valid connection strings
        (
            "fhir://epic.org/api/FHIR/R4?client_id=test&client_secret=secret&token_url=https://epic.org/token",
            True,
        ),
        (
            "fhir://localhost:8080/fhir?client_id=local&client_secret=pass&token_url=http://localhost/token",
            True,
        ),
        # Invalid connection strings
        ("http://not-fhir.com/api", False),  # Wrong scheme
        ("fhir://", False),  # Missing hostname
        ("invalid-string", False),  # Not a URL
    ],
)
def test_connection_manager_source_validation_and_parsing(
    connection_manager, connection_string, should_succeed
):
    """FHIRConnectionManager validates connection strings and parses hostnames correctly."""
    if should_succeed:
        connection_manager.add_source("test_source", connection_string)
        assert "test_source" in connection_manager.sources
        assert "test_source" in connection_manager._connection_strings
        assert (
            connection_manager._connection_strings["test_source"] == connection_string
        )
    else:
        with pytest.raises(
            FHIRConnectionError, match="Failed to parse connection string"
        ):
            connection_manager.add_source("test_source", connection_string)


async def test_connection_manager_client_retrieval_and_default_selection(
    connection_manager, mock_fhir_client
):
    """FHIRConnectionManager retrieves clients through pooling and selects defaults correctly."""
    # Add multiple sources
    connection_manager.add_source(
        "first",
        "fhir://first.com/fhir?client_id=test&client_secret=secret&token_url=https://first.com/token",
    )
    connection_manager.add_source(
        "second",
        "fhir://second.com/fhir?client_id=test&client_secret=secret&token_url=https://second.com/token",
    )

    connection_manager.client_pool.get_client = AsyncMock(return_value=mock_fhir_client)

    # Test specific source retrieval
    client = await connection_manager.get_client("first")
    assert client == mock_fhir_client

    # Test default source selection (should use first available)
    client_default = await connection_manager.get_client()
    assert client_default == mock_fhir_client
    call_args = connection_manager.client_pool.get_client.call_args
    assert "first.com" in call_args[0][0]  # Should use first source's connection string


async def test_connection_manager_error_handling_for_unknown_sources(
    connection_manager,
):
    """FHIRConnectionManager handles requests for unknown sources appropriately."""
    # Test unknown source
    with pytest.raises(ValueError, match="Unknown source: nonexistent"):
        await connection_manager.get_client("nonexistent")

    # Test source without connection string (edge case)
    connection_manager.sources["orphaned"] = None
    with pytest.raises(
        ValueError, match="No connection string found for source: orphaned"
    ):
        await connection_manager.get_client("orphaned")


@patch("healthchain.gateway.clients.create_fhir_client")
@patch("healthchain.gateway.clients.auth.parse_fhir_auth_connection_string")
def test_connection_manager_client_factory_creation(
    mock_parse_auth, mock_create_client, connection_manager
):
    """FHIRConnectionManager creates clients correctly through factory method."""
    # Setup mocks
    mock_auth_config = Mock()
    mock_parse_auth.return_value = mock_auth_config
    mock_client = Mock(spec=FHIRServerInterface)
    mock_create_client.return_value = mock_client

    # Test the factory method
    connection_string = "fhir://test.com/fhir?client_id=test&client_secret=secret&token_url=https://test.com/token"
    mock_limits = Mock()

    result = connection_manager._create_server_from_connection_string(
        connection_string, mock_limits
    )

    # Verify correct parsing and client creation
    mock_parse_auth.assert_called_once_with(connection_string)
    mock_create_client.assert_called_once_with(
        auth_config=mock_auth_config, limits=mock_limits
    )
    assert result == mock_client


def test_connection_manager_pool_status_reporting_and_sources_isolation(
    connection_manager,
):
    """FHIRConnectionManager provides pool status and isolates source data."""
    # Add test sources
    connection_manager.add_source(
        "source1",
        "fhir://test1.com/fhir?client_id=test&client_secret=secret&token_url=https://test1.com/token",
    )
    connection_manager.add_source(
        "source2",
        "fhir://test2.com/fhir?client_id=test&client_secret=secret&token_url=https://test2.com/token",
    )

    # Mock pool stats
    mock_stats = {
        "total_clients": 2,
        "limits": {
            "max_connections": 50,
            "max_keepalive_connections": 10,
            "keepalive_expiry": 30.0,
        },
        "clients": {
            "fhir://test1.com/fhir?client_id=test&client_secret=secret&token_url=https://test1.com/token": {
                "connections": 1
            },
            "fhir://test2.com/fhir?client_id=test&client_secret=secret&token_url=https://test2.com/token": {
                "connections": 2
            },
        },
    }
    connection_manager.client_pool.get_pool_stats = Mock(return_value=mock_stats)

    status = connection_manager.get_pool_status()
    assert status == mock_stats

    # Test sources isolation
    sources1 = connection_manager.get_sources()
    sources2 = connection_manager.get_sources()

    # Should be different objects (copies)
    assert sources1 is not sources2
    assert sources1 == sources2

    # Modifying returned dict shouldn't affect internal state
    sources1["modified"] = "should_not_affect_internal"
    sources3 = connection_manager.get_sources()
    assert "modified" not in sources3
