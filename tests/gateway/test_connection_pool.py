import pytest
from unittest.mock import AsyncMock, Mock

from healthchain.gateway.clients.pool import FHIRClientPool

# Configure pytest-anyio for async tests
pytestmark = pytest.mark.anyio


def test_fhir_client_pool_initialization_with_custom_limits():
    """Test FHIRClientPool configures httpx connection limits correctly."""
    pool = FHIRClientPool(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0,
    )

    assert pool._client_limits.max_connections == 100
    assert pool._client_limits.max_keepalive_connections == 20
    assert pool._client_limits.keepalive_expiry == 30.0
    assert len(pool._clients) == 0


async def test_fhir_client_pool_creates_new_client_when_none_exists():
    """Test that pool creates new clients via factory when connection string is new."""
    pool = FHIRClientPool()

    def mock_factory(connection_string, limits):
        mock_client = Mock()
        mock_client.connection_string = connection_string
        mock_client.limits = limits
        return mock_client

    connection_string = "fhir://test.com/fhir?client_id=test"
    client = await pool.get_client(connection_string, mock_factory)

    assert client.connection_string == connection_string
    assert client.limits == pool._client_limits
    assert connection_string in pool._clients


async def test_fhir_client_pool_reuses_existing_client():
    """Test that pool returns existing clients without calling factory."""
    pool = FHIRClientPool()

    # Pre-populate pool with a client
    mock_client = Mock()
    connection_string = "fhir://test.com/fhir?client_id=test"
    pool._clients[connection_string] = mock_client

    def mock_factory(connection_string, limits):
        assert False, "Factory should not be called for existing client"

    client = await pool.get_client(connection_string, mock_factory)
    assert client is mock_client


async def test_fhir_client_pool_closes_all_clients_and_clears_registry():
    """Test that closing pool properly cleans up all clients and internal state."""
    pool = FHIRClientPool()

    # Add mock clients to the pool
    mock_client1 = Mock()
    mock_client1.close = AsyncMock()
    mock_client2 = Mock()
    mock_client2.close = AsyncMock()

    pool._clients["conn1"] = mock_client1
    pool._clients["conn2"] = mock_client2

    await pool.close_all()

    mock_client1.close.assert_called_once()
    mock_client2.close.assert_called_once()
    assert len(pool._clients) == 0


def test_fhir_client_pool_statistics_reporting():
    """Test that pool provides detailed connection statistics."""
    pool = FHIRClientPool(
        max_connections=50,
        max_keepalive_connections=10,
        keepalive_expiry=15.0,
    )

    # Add mock client with pool stats
    mock_client = Mock()
    mock_client.client = Mock()
    mock_client.client._pool = Mock()
    mock_client.client._pool._pool = [Mock(), Mock()]  # 2 connections
    pool._clients["test_conn"] = mock_client

    stats = pool.get_pool_stats()

    assert stats["total_clients"] == 1
    assert stats["limits"]["max_connections"] == 50
    assert stats["limits"]["max_keepalive_connections"] == 10
    assert stats["limits"]["keepalive_expiry"] == 15.0
    assert "test_conn" in stats["clients"]
