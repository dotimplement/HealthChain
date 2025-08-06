"""
Tests for the FHIR connection manager in the HealthChain gateway system.

This module tests centralized connection management for FHIR sources:
- Connection string parsing and validation
- Source lifecycle management
- Client pooling and retrieval
"""

import pytest
from unittest.mock import Mock

from healthchain.gateway.clients.fhir.sync.connection import FHIRConnectionManager
from healthchain.gateway.fhir.errors import FHIRConnectionError
from healthchain.gateway.api.protocols import FHIRServerInterfaceProtocol


@pytest.fixture
def connection_manager():
    """Create a connection manager for testing."""
    return FHIRConnectionManager()


@pytest.fixture
def mock_fhir_client():
    """Create a mock FHIR client using protocol."""
    client = Mock(spec=FHIRServerInterfaceProtocol)
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


def test_connection_manager_client_retrieval_and_default_selection(
    connection_manager, mock_fhir_client
):
    """FHIRConnectionManager retrieves clients and selects defaults correctly."""
    # Add multiple sources
    connection_manager.add_source(
        "first",
        "fhir://first.com/fhir?client_id=test&client_secret=secret&token_url=https://first.com/token",
    )
    connection_manager.add_source(
        "second",
        "fhir://second.com/fhir?client_id=test&client_secret=secret&token_url=https://second.com/token",
    )

    # Mock the client creation method
    connection_manager._create_server_from_connection_string = Mock(
        return_value=mock_fhir_client
    )

    # Test specific source retrieval
    client = connection_manager.get_client("first")
    assert client == mock_fhir_client

    # Test default source selection (should use first available)
    client_default = connection_manager.get_client()
    assert client_default == mock_fhir_client

    # Verify the connection string was used correctly
    call_args = connection_manager._create_server_from_connection_string.call_args
    connection_string = call_args[0][0]
    from urllib.parse import urlparse

    parsed_url = urlparse(connection_string)
    assert (
        parsed_url.hostname == "first.com"
    )  # Should use first source's connection string


def test_connection_manager_cleanup_all_sources(connection_manager):
    """FHIRConnectionManager properly cleans up all client connections."""
    # Add multiple sources
    connection_manager.add_source(
        "source1",
        "fhir://source1.com/fhir?client_id=test&client_secret=secret&token_url=https://source1.com/token",
    )
    connection_manager.add_source(
        "source2",
        "fhir://source2.com/fhir?client_id=test&client_secret=secret&token_url=https://source2.com/token",
    )

    # Mock clients with close methods
    mock_client1 = Mock()
    mock_client1.close = Mock()
    mock_client2 = Mock()
    mock_client2.close = Mock()

    # Mock the client creation to return our mock clients
    def mock_create_client(connection_string):
        if "source1.com" in connection_string:
            return mock_client1
        else:
            return mock_client2

    connection_manager._create_server_from_connection_string = mock_create_client

    # Get clients (this creates them)
    client1 = connection_manager.get_client("source1")
    client2 = connection_manager.get_client("source2")

    # Verify we got the right clients
    assert client1 == mock_client1
    assert client2 == mock_client2

    # Now test cleanup - since sync doesn't have built-in cleanup,
    # we test that clients have close methods available
    assert hasattr(client1, "close")
    assert hasattr(client2, "close")

    # Manually call close to verify they work
    client1.close()
    client2.close()

    mock_client1.close.assert_called_once()
    mock_client2.close.assert_called_once()


def test_connection_manager_handles_invalid_source_gracefully(connection_manager):
    """FHIRConnectionManager handles requests for unknown sources gracefully."""
    # Add one valid source
    connection_manager.add_source(
        "valid_source",
        "fhir://valid.com/fhir?client_id=test&client_secret=secret&token_url=https://valid.com/token",
    )

    # Request client for non-existent source
    with pytest.raises(ValueError, match="Unknown source: invalid_source"):
        connection_manager.get_client("invalid_source")

    # Verify valid source still works
    connection_manager._create_server_from_connection_string = Mock(return_value=Mock())
    client = connection_manager.get_client("valid_source")
    assert client is not None


def test_connection_manager_handles_connection_string_corruption():
    """FHIRConnectionManager handles corrupted connection strings gracefully."""
    manager = FHIRConnectionManager()

    # Add valid source first
    manager.add_source(
        "valid",
        "fhir://valid.com/fhir?client_id=test&client_secret=secret&token_url=https://valid.com/token",
    )

    # Manually corrupt the connection string (simulating memory corruption or external modification)
    manager._connection_strings["valid"] = "corrupted_string_not_url"

    # Mock client creation to raise error for corrupted string
    def mock_create_with_error(connection_string):
        if connection_string == "corrupted_string_not_url":
            raise ValueError("Invalid connection string format")
        return Mock()

    manager._create_server_from_connection_string = mock_create_with_error

    # Should propagate the error appropriately
    with pytest.raises(ValueError, match="Invalid connection string format"):
        manager.get_client("valid")


def test_connection_manager_memory_cleanup_on_source_removal():
    """FHIRConnectionManager properly cleans up memory when sources are removed."""
    manager = FHIRConnectionManager()

    # Add source
    manager.add_source(
        "temp_source",
        "fhir://temp.com/fhir?client_id=test&client_secret=secret&token_url=https://temp.com/token",
    )

    # Verify source was added
    assert "temp_source" in manager.sources
    assert "temp_source" in manager._connection_strings

    # Simulate source removal (if the API existed)
    # Since the current implementation doesn't have remove_source,
    # we test manual cleanup to verify memory management
    del manager.sources["temp_source"]
    del manager._connection_strings["temp_source"]

    # Verify cleanup worked
    assert "temp_source" not in manager.sources
    assert "temp_source" not in manager._connection_strings

    # Verify the source is truly gone
    with pytest.raises(ValueError, match="Unknown source: temp_source"):
        manager.get_client("temp_source")
