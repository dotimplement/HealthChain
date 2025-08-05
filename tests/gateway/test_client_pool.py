"""Tests for FHIR client connection pooling functionality."""

import pytest
from unittest.mock import Mock, AsyncMock

from healthchain.gateway.clients.pool import ClientPool
from healthchain.gateway.api.protocols import FHIRServerInterfaceProtocol


@pytest.fixture
def mock_client_factory():
    """Create a mock client factory function."""

    def factory(connection_string, limits=None):
        client = Mock(spec=FHIRServerInterfaceProtocol)
        client.close = AsyncMock()

        # Add httpx client attributes for pool stats
        client.client = Mock()
        client.client._pool = Mock()
        available_conn = Mock()
        available_conn.is_available.return_value = True
        unavailable_conn = Mock()
        unavailable_conn.is_available.return_value = False
        client.client._pool._pool = [available_conn, unavailable_conn]

        client._limits = limits
        return client

    return factory


@pytest.fixture
def client_pool():
    """Create a ClientPool for testing."""
    return ClientPool(
        max_connections=50, max_keepalive_connections=10, keepalive_expiry=3.0
    )


@pytest.mark.parametrize(
    "max_conn,keepalive_conn,expiry",
    [
        (200, 50, 10.0),
        (100, 20, 5.0),  # defaults
    ],
)
def test_client_pool_initialization(max_conn, keepalive_conn, expiry):
    """ClientPool initializes with custom or default limits."""
    if max_conn == 100:  # test defaults
        pool = ClientPool()
    else:
        pool = ClientPool(
            max_connections=max_conn,
            max_keepalive_connections=keepalive_conn,
            keepalive_expiry=expiry,
        )

    assert pool._client_limits.max_connections == max_conn
    assert pool._client_limits.max_keepalive_connections == keepalive_conn
    assert pool._client_limits.keepalive_expiry == expiry
    assert pool._clients == {}


@pytest.mark.asyncio
async def test_client_creation_and_reuse(client_pool, mock_client_factory):
    """ClientPool creates new clients and reuses existing ones."""
    conn1 = "fhir://server1.example.com/R4"
    conn2 = "fhir://server2.example.com/R4"

    # Create first client
    client1a = await client_pool.get_client(conn1, mock_client_factory)
    assert client1a is not None
    assert conn1 in client_pool._clients
    assert client1a._limits is client_pool._client_limits

    # Reuse same client
    client1b = await client_pool.get_client(conn1, mock_client_factory)
    assert client1a is client1b

    # Create different client for different connection
    client2 = await client_pool.get_client(conn2, mock_client_factory)
    assert client1a is not client2
    assert len(client_pool._clients) == 2


@pytest.mark.asyncio
async def test_close_all_clients(client_pool, mock_client_factory):
    """ClientPool closes all clients and handles missing close methods."""
    conn1 = "fhir://server1.example.com/R4"
    conn2 = "fhir://server2.example.com/R4"

    # Create clients
    client1 = await client_pool.get_client(conn1, mock_client_factory)
    client2 = await client_pool.get_client(conn2, mock_client_factory)

    # Add client without close method
    client_without_close = Mock(spec=[])
    client_pool._clients["no_close"] = client_without_close

    # Close all clients
    await client_pool.close_all()

    # Verify all clients were closed
    client1.close.assert_called_once()
    client2.close.assert_called_once()
    assert client_pool._clients == {}


@pytest.mark.asyncio
async def test_pool_stats(client_pool, mock_client_factory):
    """ClientPool provides accurate statistics."""
    # Empty pool stats
    stats = client_pool.get_pool_stats()
    assert stats["total_clients"] == 0
    assert stats["limits"]["max_connections"] == 50
    assert stats["limits"]["max_keepalive_connections"] == 10
    assert stats["limits"]["keepalive_expiry"] == 3.0
    assert stats["clients"] == {}

    # Add clients and check stats
    conn1 = "fhir://server1.example.com/R4"
    conn2 = "fhir://server2.example.com/R4"

    await client_pool.get_client(conn1, mock_client_factory)
    await client_pool.get_client(conn2, mock_client_factory)

    stats = client_pool.get_pool_stats()
    assert stats["total_clients"] == 2
    assert conn1 in stats["clients"]
    assert conn2 in stats["clients"]

    # Check connection details
    client_stats = stats["clients"][conn1]
    assert client_stats["active_connections"] == 2
    assert client_stats["available_connections"] == 1


@pytest.mark.asyncio
async def test_pool_stats_without_pool_info(client_pool):
    """ClientPool handles clients without connection pool info."""
    simple_client = Mock(spec=[])
    client_pool._clients["simple"] = simple_client

    stats = client_pool.get_pool_stats()
    assert stats["total_clients"] == 1
    assert stats["clients"]["simple"] == {}


@pytest.mark.asyncio
async def test_client_factory_exceptions(client_pool):
    """ClientPool propagates exceptions from client factory."""

    def failing_factory(connection_string, limits=None):
        raise ValueError("Factory failed")

    with pytest.raises(ValueError, match="Factory failed"):
        await client_pool.get_client("fhir://test.com/R4", failing_factory)


@pytest.mark.asyncio
async def test_concurrent_client_creation(client_pool):
    """ClientPool handles concurrent requests for same connection."""
    connection_string = "fhir://test.example.com/R4"
    call_count = 0

    def counting_factory(conn_str, limits=None):
        nonlocal call_count
        call_count += 1
        client = Mock()
        client.close = AsyncMock()
        return client

    import asyncio

    async def get_client():
        return await client_pool.get_client(connection_string, counting_factory)

    # Create concurrent tasks
    tasks = [get_client() for _ in range(3)]
    results = await asyncio.gather(*tasks)

    # All clients should be the same instance
    assert all(client is results[0] for client in results)
    # Factory should only be called once due to caching
    assert call_count == 1
