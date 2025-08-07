import httpx

from typing import Any, Callable, Dict, TypeVar, Generic

# Generic client interface type
ClientInterface = TypeVar("ClientInterface")


class ClientPool(Generic[ClientInterface]):
    """
    Generic client pool for managing client instances with connection pooling using httpx.
    Handles connection lifecycle, timeouts, and resource cleanup for any client type.
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 5.0,
    ):
        """
        Initialize the client pool.

        Args:
            max_connections: Maximum number of total connections
            max_keepalive_connections: Maximum number of keep-alive connections
            keepalive_expiry: How long to keep connections alive (seconds)
        """
        self._clients: Dict[str, ClientInterface] = {}
        self._client_limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )

    async def get_client(
        self, connection_string: str, client_factory: Callable
    ) -> ClientInterface:
        """
        Get a client for the given connection string.

        Args:
            connection_string: Connection string for the client
            client_factory: Factory function to create new clients

        Returns:
            ClientInterface: A client with pooled connections
        """
        if connection_string not in self._clients:
            # Create new client with connection pooling
            self._clients[connection_string] = client_factory(
                connection_string, limits=self._client_limits
            )

        return self._clients[connection_string]

    async def close_all(self):
        """Close all client connections."""
        for client in self._clients.values():
            if hasattr(client, "close"):
                await client.close()
        self._clients.clear()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        stats = {
            "total_clients": len(self._clients),
            "limits": {
                "max_connections": self._client_limits.max_connections,
                "max_keepalive_connections": self._client_limits.max_keepalive_connections,
                "keepalive_expiry": self._client_limits.keepalive_expiry,
            },
            "clients": {},
        }

        for conn_str, client in self._clients.items():
            # Try to get httpx client stats if available
            client_stats = {}
            if hasattr(client, "client") and hasattr(client.client, "_pool"):
                pool = client.client._pool
                client_stats.update(
                    {
                        "active_connections": len(pool._pool),
                        "available_connections": len(
                            [c for c in pool._pool if c.is_available()]
                        ),
                    }
                )
            stats["clients"][conn_str] = client_stats

        return stats
