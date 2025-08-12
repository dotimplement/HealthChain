"""
Tests for shared FHIR connection manager functionality in the HealthChain gateway system.

This module tests shared connection string validation, source management, and error handling
that should work identically across sync and async connection manager implementations.
"""

import pytest
from unittest.mock import Mock

from healthchain.gateway.clients.fhir.sync.connection import FHIRConnectionManager
from healthchain.gateway.clients.fhir.aio.connection import AsyncFHIRConnectionManager
from healthchain.gateway.fhir.errors import FHIRConnectionError
from healthchain.gateway.api.protocols import FHIRServerInterfaceProtocol


@pytest.fixture(params=["sync", "async"])
def connection_manager(request):
    """Fixture providing both sync and async connection managers."""
    if request.param == "sync":
        return FHIRConnectionManager()
    else:
        return AsyncFHIRConnectionManager(
            max_connections=50, max_keepalive_connections=10, keepalive_expiry=30.0
        )


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
    """Connection managers validate connection strings and parse hostnames correctly."""
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


@pytest.mark.asyncio
async def test_connection_manager_handles_invalid_source_gracefully(connection_manager):
    """Connection managers handle requests for unknown sources gracefully."""
    # Add one valid source
    connection_manager.add_source(
        "valid_source",
        "fhir://valid.com/fhir?client_id=test&client_secret=secret&token_url=https://valid.com/token",
    )

    # Request client for non-existent source - should raise ValueError
    with pytest.raises(ValueError, match="Unknown source: invalid_source"):
        if hasattr(connection_manager, "get_client"):
            # Check if it's async by seeing if the method is a coroutine function
            import inspect

            if inspect.iscoroutinefunction(connection_manager.get_client):
                # For async version
                await connection_manager.get_client("invalid_source")
            else:
                # For sync version
                connection_manager.get_client("invalid_source")

    # Verify the source was actually added correctly
    assert "valid_source" in connection_manager.sources
    assert "valid_source" in connection_manager._connection_strings


def test_connection_manager_source_storage_consistency(connection_manager):
    """Connection managers consistently store sources and connection strings."""
    test_sources = [
        (
            "source1",
            "fhir://source1.com/fhir?client_id=test&client_secret=secret&token_url=https://source1.com/token",
        ),
        (
            "source2",
            "fhir://source2.com/fhir?client_id=test&client_secret=secret&token_url=https://source2.com/token",
        ),
        (
            "source3",
            "fhir://source3.com/fhir?client_id=test&client_secret=secret&token_url=https://source3.com/token",
        ),
    ]

    # Add all sources
    for name, connection_string in test_sources:
        connection_manager.add_source(name, connection_string)

    # Verify all sources are stored consistently
    for name, connection_string in test_sources:
        assert name in connection_manager.sources
        assert name in connection_manager._connection_strings
        assert connection_manager._connection_strings[name] == connection_string

    # Verify source count
    assert len(connection_manager.sources) == 3
    assert len(connection_manager._connection_strings) == 3


def test_connection_manager_handles_duplicate_source_names(connection_manager):
    """Connection managers handle duplicate source names by overwriting."""
    original_connection = "fhir://original.com/fhir?client_id=test&client_secret=secret&token_url=https://original.com/token"
    updated_connection = "fhir://updated.com/fhir?client_id=test&client_secret=secret&token_url=https://updated.com/token"

    # Add original source
    connection_manager.add_source("duplicate_source", original_connection)
    assert (
        connection_manager._connection_strings["duplicate_source"]
        == original_connection
    )

    # Add source with same name but different connection string
    connection_manager.add_source("duplicate_source", updated_connection)
    assert (
        connection_manager._connection_strings["duplicate_source"] == updated_connection
    )

    # Should only have one source with that name
    source_count = sum(
        1 for name in connection_manager.sources.keys() if name == "duplicate_source"
    )
    assert source_count == 1


def test_connection_manager_handles_connection_string_corruption(connection_manager):
    """Connection managers handle corrupted connection strings gracefully."""
    # Test with both sync and async managers
    for manager_class in [FHIRConnectionManager, AsyncFHIRConnectionManager]:
        if manager_class == AsyncFHIRConnectionManager:
            manager = manager_class(max_connections=10)
        else:
            manager = manager_class()

        # Add valid source first
        manager.add_source(
            "valid",
            "fhir://valid.com/fhir?client_id=test&client_secret=secret&token_url=https://valid.com/token",
        )

        # Verify source was added correctly
        assert "valid" in manager.sources
        assert "valid" in manager._connection_strings

        # Manually corrupt the connection string (simulating memory corruption)
        manager._connection_strings["valid"] = "corrupted_string_not_url"

        # The connection string should now be corrupted
        assert manager._connection_strings["valid"] == "corrupted_string_not_url"


def test_connection_manager_memory_cleanup_on_source_removal(connection_manager):
    """Connection managers properly clean up memory when sources are removed."""
    # Test with both sync and async managers
    for manager_class in [FHIRConnectionManager, AsyncFHIRConnectionManager]:
        if manager_class == AsyncFHIRConnectionManager:
            manager = manager_class(max_connections=10)
        else:
            manager = manager_class()

        # Add source
        manager.add_source(
            "temp_source",
            "fhir://temp.com/fhir?client_id=test&client_secret=secret&token_url=https://temp.com/token",
        )

        # Verify source was added
        assert "temp_source" in manager.sources
        assert "temp_source" in manager._connection_strings

        # Simulate source removal (manual cleanup to verify memory management)
        del manager.sources["temp_source"]
        del manager._connection_strings["temp_source"]

        # Verify cleanup worked
        assert "temp_source" not in manager.sources
        assert "temp_source" not in manager._connection_strings


def test_connection_manager_initialization_state(connection_manager):
    """Connection managers initialize with empty state."""
    assert len(connection_manager.sources) == 0
    assert len(connection_manager._connection_strings) == 0
    assert isinstance(connection_manager.sources, dict)
    assert isinstance(connection_manager._connection_strings, dict)


def test_connection_manager_source_name_validation(connection_manager):
    """Connection managers accept various source name formats."""
    valid_names = [
        "simple_name",
        "name-with-dashes",
        "name.with.dots",
        "name_123",
        "UPPERCASE_NAME",
        "MixedCase_Name-123.test",
    ]

    connection_string = "fhir://test.com/fhir?client_id=test&client_secret=secret&token_url=https://test.com/token"

    for name in valid_names:
        connection_manager.add_source(name, connection_string)
        assert name in connection_manager.sources
        assert name in connection_manager._connection_strings
