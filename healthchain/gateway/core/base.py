"""
Base classes for the HealthChain Gateway.

This module provides the core abstract base classes that define the
architecture of the gateway system.
"""

from abc import ABC
from typing import Any, Callable, List, TypeVar
import logging
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="StandardAdapter")


class StandardAdapter(ABC):
    """
    Base class for healthcare standard adapters that handle communication with external systems.

    Adapters provide a consistent interface for interacting with healthcare standards
    and protocols through the decorator pattern for handler registration.
    """

    def __init__(self, **options):
        """
        Initialize a new standard adapter.

        Args:
            **options: Configuration options for the adapter
        """
        self._handlers = {}
        self.options = options
        # Default to raising exceptions, but allow configuration
        self.return_errors = options.get("return_errors", False)

    def register_handler(self, operation: str, handler: Callable) -> T:
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
        Handle an operation using registered handlers.
        Supports both synchronous and asynchronous handlers.
        """
        if operation in self._handlers:
            handler = self._handlers[operation]
            # Support both async and non-async handlers
            if asyncio.iscoroutinefunction(handler):
                return await handler(**params)
            else:
                return handler(**params)

        # Fall back to default handler
        if asyncio.iscoroutinefunction(self._default_handler):
            return await self._default_handler(operation, **params)
        else:
            return self._default_handler(operation, **params)

    async def _default_handler(self, operation: str, **params) -> Any:
        """
        Default handler for operations without registered handlers.
        """
        message = f"Unsupported operation: {operation}"
        logger.warning(message)

        if self.return_errors:
            return {"error": message}
        else:
            raise ValueError(message)


class InboundAdapter(StandardAdapter):
    """
    Specialized adapter for handling inbound requests from external healthcare systems.

    Inbound adapters receive and process requests according to specific healthcare
    standards (like SOAP, CDS Hooks) and serve as entry points for external systems.
    """

    def get_capabilities(self) -> List[str]:
        """
        Get list of operations this adapter supports.

        Returns:
            List of supported operation names
        """
        return list(self._handlers.keys())


class OutboundAdapter(StandardAdapter):
    """
    Specialized adapter for initiating outbound requests to external healthcare systems.

    Outbound adapters make requests to external systems (like FHIR servers)
    and handle communication according to their specific standards and protocols.
    """

    pass
