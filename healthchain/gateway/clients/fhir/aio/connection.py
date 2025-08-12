import httpx

from typing import Dict

from healthchain.gateway.clients.fhir.base import FHIRServerInterface
from healthchain.gateway.clients.pool import ClientPool
from healthchain.gateway.clients.fhir.sync.connection import FHIRConnectionManager


class AsyncFHIRConnectionManager(FHIRConnectionManager):
    """
    Async FHIR connection manager with connection pooling.

    Handles connection strings, source configuration, and provides
    pooled async FHIR clients for efficient resource management.
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 5.0,
    ):
        """
        Initialize the async connection manager.

        Args:
            max_connections: Maximum total HTTP connections across all sources
            max_keepalive_connections: Maximum keep-alive connections per source
            keepalive_expiry: How long to keep connections alive (seconds)
        """
        super().__init__()

        # Create httpx-based client pool
        self.client_pool = ClientPool(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )

    async def close(self):
        """Close all connections and clean up resources."""
        await self.client_pool.close_all()

    def get_status(self) -> Dict[str, any]:
        """
        Get the current status of the async connection manager.

        Returns:
            Dict containing status information including pool stats.
        """
        status = {
            "client_type": "async",
            "pooling_enabled": True,
            "sources": {
                "count": len(self.sources),
                "configured": list(self.sources.keys()),
                "connection_strings": {
                    name: f"fhir://{name}/*" for name in self.sources.keys()
                },
            },
            "pool_stats": self.client_pool.get_pool_stats(),
        }
        return status

    async def get_client(self, source: str = None) -> FHIRServerInterface:
        """
        Get an async FHIR client for the specified source.

        Args:
            source: Source name to get client for (uses first available if None)

        Returns:
            FHIRServerInterface: An async FHIR client with pooled connections

        Raises:
            ValueError: If source is unknown or no connection string found
        """
        source_name = source or next(iter(self.sources.keys()))
        if source_name not in self.sources:
            raise ValueError(f"Unknown source: {source_name}")

        if source_name not in self._connection_strings:
            raise ValueError(f"No connection string found for source: {source_name}")

        connection_string = self._connection_strings[source_name]

        return await self.client_pool.get_client(
            connection_string, self._create_server_from_connection_string
        )

    def _create_server_from_connection_string(
        self, connection_string: str, limits: httpx.Limits = None
    ) -> FHIRServerInterface:
        """
        Create an async FHIR server instance from a connection string with connection pooling.

        This is used by the client pool to create new server instances.

        Args:
            connection_string: FHIR connection string
            limits: httpx connection limits for pooling

        Returns:
            FHIRServerInterface: A new async FHIR server instance with pooled connections
        """
        from healthchain.gateway.clients.fhir.aio.client import create_async_fhir_client
        from healthchain.gateway.clients.fhir.base import (
            parse_fhir_auth_connection_string,
        )

        # Parse connection string as OAuth2.0 configuration
        auth_config = parse_fhir_auth_connection_string(connection_string)

        # Pass httpx limits for connection pooling
        return create_async_fhir_client(auth_config=auth_config, limits=limits)
