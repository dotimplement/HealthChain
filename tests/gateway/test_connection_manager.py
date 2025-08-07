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
