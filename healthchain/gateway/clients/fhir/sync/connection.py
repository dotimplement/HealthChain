import logging
import urllib.parse

from typing import Dict

from healthchain.gateway.clients.fhir.base import FHIRServerInterface
from healthchain.gateway.fhir.errors import FHIRConnectionError


logger = logging.getLogger(__name__)


class FHIRConnectionManager:
    """
    Base FHIR connection manager for sync clients.

    Handles connection strings, source configuration, and provides
    sync FHIR clients.
    """

    def __init__(self):
        """Initialize the sync connection manager."""
        # Store configuration
        self.sources = {}
        self._connection_strings = {}

    def add_source(self, name: str, connection_string: str):
        """
        Add a FHIR data source using connection string.

        Format: fhir://hostname:port/path?param1=value1&param2=value2

        Examples:
            fhir://epic.org/api/FHIR/R4?client_id=my_app&client_secret=secret&token_url=https://epic.org/oauth2/token&use_jwt_assertion=true
            fhir://cerner.org/r4?client_id=app_id&client_secret=app_secret&token_url=https://cerner.org/token&scope=openid

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

            # Store the source name
            self.sources[name] = None  # Placeholder - store metadata here

            logger.info(f"Added FHIR source '{name}'")

        except Exception as e:
            raise FHIRConnectionError(
                message=f"Failed to parse connection string: {str(e)}",
                code="Invalid connection string",
                state="500",
            )

    def get_client(self, source: str = None) -> FHIRServerInterface:
        """
        Get a sync FHIR client for the specified source.

        Args:
            source: Source name to get client for (uses first available if None)

        Returns:
            FHIRServerInterface: A sync FHIR client

        Raises:
            ValueError: If source is unknown or no connection string found
        """
        source_name = source or next(iter(self.sources.keys()))
        if source_name not in self.sources:
            raise ValueError(f"Unknown source: {source_name}")

        if source_name not in self._connection_strings:
            raise ValueError(f"No connection string found for source: {source_name}")

        connection_string = self._connection_strings[source_name]

        return self._create_server_from_connection_string(connection_string)

    def get_status(self) -> Dict[str, any]:
        """
        Get the current status of the sync connection manager.

        Returns:
            Dict containing status information for sync clients.
        """
        return {
            "client_type": "sync",
            "pooling_enabled": False,
            "sources": {
                "count": len(self.sources),
                "configured": list(self.sources.keys()),
            },
        }

    def get_sources(self) -> Dict[str, any]:
        """
        Get all configured sources.

        Returns:
            Dict of source names and their configurations
        """
        return self.sources.copy()

    def _create_server_from_connection_string(
        self, connection_string: str
    ) -> FHIRServerInterface:
        """
        Create a sync FHIR server instance from a connection string.

        Args:
            connection_string: FHIR connection string

        Returns:
            FHIRServerInterface: A new sync FHIR server instance
        """
        from healthchain.gateway.clients.fhir.sync.client import create_fhir_client
        from healthchain.gateway.clients.fhir.base import (
            parse_fhir_auth_connection_string,
        )

        # Parse connection string as OAuth2.0 configuration
        auth_config = parse_fhir_auth_connection_string(connection_string)

        return create_fhir_client(auth_config=auth_config)
