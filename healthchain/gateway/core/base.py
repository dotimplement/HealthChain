"""
Base classes for the HealthChain Gateway.

This module provides the core abstract base classes that define the
architecture of the gateway system.
"""

from abc import ABC
from typing import Any, Callable, List
import logging

logger = logging.getLogger(__name__)


class ProtocolService(ABC):
    """
    Base class for inbound protocol services that handle external requests.

    Protocol services receive and process requests according to specific
    healthcare standards and protocols (SOAP, CDS Hooks) from external systems.

    These components implement the decorator pattern for handler registration
    and serve as the entry point for external healthcare systems.
    """

    def __init__(self, **options):
        """
        Initialize a new protocol service.

        Args:
            **options: Configuration options for the service
        """
        self._handlers = {}
        self.options = options

    def register_handler(self, operation: str, handler: Callable) -> "ProtocolService":
        """
        Register a handler function for a specific operation.

        Args:
            operation: The operation name or identifier
            handler: Function that will handle the operation

        Returns:
            Self, to allow for method chaining
        """
        self._handlers[operation] = handler
        return self

    async def handle(self, operation: str, **params) -> Any:
        """
        Handle an incoming request using registered handlers.

        Args:
            operation: The operation to perform
            **params: Parameters for the operation

        Returns:
            Result of the operation
        """
        if operation in self._handlers:
            return await self._handlers[operation](**params)

        # Fall back to default handler
        return await self._default_handler(operation, **params)

    async def _default_handler(self, operation: str, **params) -> Any:
        """
        Default handler for operations without registered handlers.

        Args:
            operation: The operation name
            **params: Operation parameters

        Returns:
            Default operation result

        Raises:
            ValueError: If the operation is not supported
        """
        raise ValueError(f"Unsupported operation: {operation}")

    def get_capabilities(self) -> List[str]:
        """
        Get list of operations this protocol service supports.

        Returns:
            List of supported operation names
        """
        return list(self._handlers.keys())


class ClientConnector(ABC):
    """
    Base class for outbound client connectors that initiate requests.

    Client connectors make requests to external healthcare systems
    and provide a consistent interface for interacting with them.

    These components implement the decorator pattern for operation registration
    and handle outbound communication to external systems.
    """

    def __init__(self, **options):
        """
        Initialize a new client connector.

        Args:
            **options: Configuration options for the client
        """
        self._handlers = {}
        self.options = options

    def register_handler(self, operation: str, handler: Callable) -> "ClientConnector":
        """
        Register a handler function for a specific operation.

        Args:
            operation: The operation name or identifier
            handler: Function that will handle the operation

        Returns:
            Self, to allow for method chaining
        """
        self._handlers[operation] = handler
        return self

    async def handle(self, operation: str, **params) -> Any:
        """
        Perform an outbound operation using registered handlers.

        Args:
            operation: The operation to perform
            **params: Parameters for the operation

        Returns:
            Result of the operation
        """
        if operation in self._handlers:
            return await self._handlers[operation](**params)

        # Fall back to default handler
        return await self._default_handler(operation, **params)

    async def _default_handler(self, operation: str, **params) -> Any:
        """
        Default handler for operations without registered handlers.

        Args:
            operation: The operation name
            **params: Operation parameters

        Returns:
            Default operation result

        Raises:
            ValueError: If the operation is not supported
        """
        raise ValueError(f"Unsupported operation: {operation}")

    def get_capabilities(self) -> List[str]:
        """
        Get list of operations this client connector supports.

        Returns:
            List of supported operation names
        """
        return list(self._handlers.keys())
