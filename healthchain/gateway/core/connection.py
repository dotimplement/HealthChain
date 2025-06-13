"""
FHIR Connection Management for HealthChain Gateway.

This module provides centralized connection management for FHIR sources,
including connection string parsing, client pooling, and source configuration.
"""

import logging
import urllib.parse
from typing import Dict

import httpx

from typing import TYPE_CHECKING

from healthchain.gateway.clients.fhir import FHIRServerInterface
from healthchain.gateway.clients.pool import FHIRClientPool
from healthchain.gateway.core.errors import FHIRConnectionError

if TYPE_CHECKING:
    from healthchain.gateway.clients.auth import FHIRAuthConfig

logger = logging.getLogger(__name__)


class FHIRConnectionManager:
    """
    Manages FHIR connections and client pooling.

    Handles connection strings, source configuration, and provides
    pooled FHIR clients for efficient resource management.
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 5.0,
    ):
        """
        Initialize the connection manager.

        Args:
            max_connections: Maximum total HTTP connections across all sources
            max_keepalive_connections: Maximum keep-alive connections per source
            keepalive_expiry: How long to keep connections alive (seconds)
        """
        # Create httpx-based client pool
        self.client_pool = FHIRClientPool(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )

        # Store configuration
        self.sources = {}
        self._connection_strings = {}

    def add_source(self, name: str, connection_string: str):
        """
        Add a FHIR data source using connection string with OAuth2.0 flow.

        Format: fhir://hostname:port/path?param1=value1&param2=value2

        Examples:
            fhir://epic.org/api/FHIR/R4?client_id=my_app&client_secret=secret&token_url=https://epic.org/oauth2/token&scope=system/*.read
            fhir://cerner.org/r4?client_id=app_id&client_secret=app_secret&token_url=https://cerner.org/token&audience=https://cerner.org/fhir

        Args:
            name: Source name identifier
            connection_string: FHIR connection string

        Raises:
            FHIRConnectionError: If connection string is invalid
        """
        # Store connection string for pooling
        self._connection_strings[name] = connection_string

        # Parse the connection string for validation only
        try:
            if not connection_string.startswith("fhir://"):
                raise ValueError("Connection string must start with fhir://")

            # Parse URL for validation
            parsed = urllib.parse.urlparse(connection_string)

            # Validate that we have a valid hostname
            if not parsed.netloc:
                raise ValueError("Invalid connection string: missing hostname")

            # Store the source name - actual connections will be managed by the pool
            self.sources[name] = (
                None  # Placeholder - pool will manage actual connections
            )

            logger.info(f"Added FHIR source '{name}' with connection pooling enabled")

        except Exception as e:
            raise FHIRConnectionError(
                message=f"Failed to parse connection string: {str(e)}",
                code="Invalid connection string",
                state="500",
            )

    def add_source_config(self, name: str, auth_config: "FHIRAuthConfig"):
        """
        Add a FHIR data source using a configuration object.

        This is an alternative to connection strings for those who prefer
        explicit configuration objects.

        Args:
            name: Source name
            auth_config: FHIRAuthConfig object with OAuth2 settings

        Example:
            from healthchain.gateway.clients.auth import FHIRAuthConfig

            config = FHIRAuthConfig(
                client_id="your_client_id",
                client_secret="your_client_secret",
                token_url="https://epic.com/oauth2/token",
                base_url="https://epic.com/api/FHIR/R4",
                scope="system/Patient.read"
            )
            connection_manager.add_source_config("epic", config)
        """
        from healthchain.gateway.clients.auth import FHIRAuthConfig

        if not isinstance(auth_config, FHIRAuthConfig):
            raise ValueError("auth_config must be a FHIRAuthConfig instance")

        # Store the config for connection pooling
        # Create a synthetic connection string for internal storage
        connection_string = (
            f"fhir://{auth_config.base_url.replace('https://', '').replace('http://', '')}?"
            f"client_id={auth_config.client_id}&"
            f"client_secret={auth_config.client_secret}&"
            f"token_url={auth_config.token_url}&"
            f"scope={auth_config.scope or ''}&"
            f"timeout={auth_config.timeout}&"
            f"verify_ssl={auth_config.verify_ssl}&"
            f"use_jwt_assertion={auth_config.use_jwt_assertion}"
        )

        if auth_config.audience:
            connection_string += f"&audience={auth_config.audience}"

        self._connection_strings[name] = connection_string
        self.sources[name] = None  # Placeholder for pool management

        logger.info(f"Added FHIR source '{name}' using configuration object")

    def add_source_from_env(self, name: str, env_prefix: str):
        """
        Add a FHIR data source using environment variables.

        This method reads OAuth2.0 configuration from environment variables
        with a given prefix.

        Args:
            name: Source name
            env_prefix: Environment variable prefix (e.g., "EPIC")

        Expected environment variables:
            {env_prefix}_CLIENT_ID
            {env_prefix}_CLIENT_SECRET
            {env_prefix}_TOKEN_URL
            {env_prefix}_BASE_URL
            {env_prefix}_SCOPE (optional)
            {env_prefix}_AUDIENCE (optional)
            {env_prefix}_TIMEOUT (optional, default: 30)
            {env_prefix}_VERIFY_SSL (optional, default: true)
            {env_prefix}_USE_JWT_ASSERTION (optional, default: false)

        Example:
            # Set environment variables:
            # EPIC_CLIENT_ID=app123
            # EPIC_CLIENT_SECRET=secret456
            # EPIC_TOKEN_URL=https://epic.com/oauth2/token
            # EPIC_BASE_URL=https://epic.com/api/FHIR/R4

            connection_manager.add_source_from_env("epic", "EPIC")
        """
        import os
        from healthchain.gateway.clients.auth import FHIRAuthConfig

        # Read required environment variables
        client_id = os.getenv(f"{env_prefix}_CLIENT_ID")
        client_secret = os.getenv(f"{env_prefix}_CLIENT_SECRET")
        token_url = os.getenv(f"{env_prefix}_TOKEN_URL")
        base_url = os.getenv(f"{env_prefix}_BASE_URL")

        if not all([client_id, client_secret, token_url, base_url]):
            missing = [
                var
                for var, val in [
                    (f"{env_prefix}_CLIENT_ID", client_id),
                    (f"{env_prefix}_CLIENT_SECRET", client_secret),
                    (f"{env_prefix}_TOKEN_URL", token_url),
                    (f"{env_prefix}_BASE_URL", base_url),
                ]
                if not val
            ]
            raise ValueError(f"Missing required environment variables: {missing}")

        # Read optional environment variables
        scope = os.getenv(f"{env_prefix}_SCOPE", "system/*.read")
        audience = os.getenv(f"{env_prefix}_AUDIENCE")
        timeout = int(os.getenv(f"{env_prefix}_TIMEOUT", "30"))
        verify_ssl = os.getenv(f"{env_prefix}_VERIFY_SSL", "true").lower() == "true"
        use_jwt_assertion = (
            os.getenv(f"{env_prefix}_USE_JWT_ASSERTION", "false").lower() == "true"
        )

        # Create configuration object
        config = FHIRAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            base_url=base_url,
            scope=scope,
            audience=audience,
            timeout=timeout,
            verify_ssl=verify_ssl,
            use_jwt_assertion=use_jwt_assertion,
        )

        # Add the source using the config object
        self.add_source_config(name, config)

        logger.info(
            f"Added FHIR source '{name}' from environment variables with prefix '{env_prefix}'"
        )

    def _create_server_from_connection_string(
        self, connection_string: str, limits: httpx.Limits = None
    ) -> FHIRServerInterface:
        """
        Create a FHIR server instance from a connection string with connection pooling.

        This is used by the client pool to create new server instances.

        Args:
            connection_string: FHIR connection string
            limits: httpx connection limits for pooling

        Returns:
            FHIRServerInterface: A new FHIR server instance with pooled connections
        """
        from healthchain.gateway.clients import create_fhir_client
        from healthchain.gateway.clients.auth import parse_fhir_auth_connection_string

        # Parse connection string as OAuth2.0 configuration
        auth_config = parse_fhir_auth_connection_string(connection_string)

        # Pass httpx limits for connection pooling
        return create_fhir_client(auth_config=auth_config, limits=limits)

    async def get_client(self, source: str = None) -> FHIRServerInterface:
        """
        Get a FHIR client for the specified source.

        Connections are automatically pooled and managed by httpx.

        Args:
            source: Source name to get client for (uses first available if None)

        Returns:
            FHIRServerInterface: A FHIR client with pooled connections

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

    def get_pool_status(self) -> Dict[str, any]:
        """
        Get the current status of the connection pool.

        Returns:
            Dict containing pool status information including:
            - max_connections: Maximum connections across all sources
            - sources: Dict of source names and their connection info
            - client_stats: Detailed httpx connection pool statistics
        """
        return self.client_pool.get_pool_stats()

    def get_sources(self) -> Dict[str, any]:
        """
        Get all configured sources.

        Returns:
            Dict of source names and their configurations
        """
        return self.sources.copy()

    async def close(self):
        """Close all connections and clean up resources."""
        await self.client_pool.close_all()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
