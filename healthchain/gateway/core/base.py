"""
Base classes for the HealthChain Gateway.

This module provides the core abstract base classes that define the
architecture of the gateway system.
"""

import logging
import asyncio

from abc import ABC
from typing import Any, Callable, Dict, List, TypeVar, Generic, Optional, Union, Type
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Type variables for self-referencing return types and generic adapters
A = TypeVar("A", bound="StandardAdapter")
T = TypeVar("T")  # For generic request types
R = TypeVar("R")  # For generic response types


class AdapterConfig(BaseModel):
    """Base configuration class for adapters"""

    return_errors: bool = False
    system_type: str = "GENERIC"


class StandardAdapter(ABC, Generic[T, R]):
    """
    Base class for healthcare standard adapters that handle communication with external systems.

    Adapters provide a consistent interface for interacting with healthcare standards
    and protocols through the decorator pattern for handler registration.

    Type Parameters:
        T: The request type this adapter handles
        R: The response type this adapter returns
    """

    def __init__(self, config: Optional[AdapterConfig] = None, **options):
        """
        Initialize a new standard adapter.

        Args:
            config: Configuration options for the adapter
            **options: Additional configuration options
        """
        self._handlers = {}
        self.options = options
        self.config = config or AdapterConfig()
        # Default to raising exceptions unless configured otherwise
        self.return_errors = self.config.return_errors or options.get(
            "return_errors", False
        )

    def register_handler(self, operation: str, handler: Callable) -> A:
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

    async def handle(self, operation: str, **params) -> Union[R, Dict[str, Any]]:
        """
        Handle an operation using registered handlers.
        Supports both synchronous and asynchronous handlers.

        Args:
            operation: The operation name to handle
            **params: Parameters to pass to the handler

        Returns:
            The response object or error dictionary
        """
        if operation in self._handlers:
            handler = self._handlers[operation]
            try:
                # Support both async and non-async handlers
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**params)
                else:
                    result = handler(**params)
                return self._process_result(result)
            except Exception as e:
                logger.error(
                    f"Error in handler for operation {operation}: {str(e)}",
                    exc_info=True,
                )
                return self._handle_error(str(e))

        # Fall back to default handler
        if asyncio.iscoroutinefunction(self._default_handler):
            return await self._default_handler(operation, **params)
        else:
            return self._default_handler(operation, **params)

    def _process_result(self, result: Any) -> R:
        """
        Process the result from a handler to ensure it matches the expected response type.

        Override this in subclasses to implement specific result processing logic.

        Args:
            result: The raw result from the handler

        Returns:
            Processed result in the expected response format
        """
        return result

    def _handle_error(self, error_message: str) -> Union[R, Dict[str, Any]]:
        """
        Handle errors that occur during handler execution.

        Args:
            error_message: The error message

        Returns:
            Error response in the appropriate format
        """
        message = f"Error during operation execution: {error_message}"
        logger.warning(message)

        if self.return_errors:
            return {"error": message}
        else:
            raise ValueError(message)

    async def _default_handler(
        self, operation: str, **params
    ) -> Union[R, Dict[str, Any]]:
        """
        Default handler for operations without registered handlers.

        Args:
            operation: The operation name
            **params: Parameters passed to the operation

        Returns:
            Error response indicating unsupported operation
        """
        message = f"Unsupported operation: {operation}"
        logger.warning(message)

        if self.return_errors:
            return {"error": message}
        else:
            raise ValueError(message)


class InboundAdapter(StandardAdapter[T, R]):
    """
    Specialized adapter for handling inbound requests from external healthcare systems.

    Inbound adapters receive and process requests according to specific healthcare
    standards (like SOAP, CDS Hooks) and serve as entry points for external systems.

    Type Parameters:
        T: The request type this adapter handles
        R: The response type this adapter returns
    """

    def get_capabilities(self) -> List[str]:
        """
        Get list of operations this adapter supports.

        Returns:
            List of supported operation names
        """
        return list(self._handlers.keys())


class OutboundAdapter(StandardAdapter[T, R]):
    """
    Specialized adapter for initiating outbound requests to external healthcare systems.

    Outbound adapters make requests to external systems (like FHIR servers)
    and handle communication according to their specific standards and protocols.

    Type Parameters:
        T: The request type this adapter handles
        R: The response type this adapter returns
    """

    pass


class BaseService(ABC):
    """
    Base class for all gateway services.

    Services handle protocol-specific concerns and provide integration with
    web frameworks like FastAPI. They typically use adapters for the actual
    handler registration and execution.
    """

    def __init__(self, adapter: StandardAdapter, event_dispatcher: Any = None):
        """
        Initialize a new service.

        Args:
            adapter: Adapter instance for handling requests
            event_dispatcher: Optional event dispatcher for publishing events
        """
        self.adapter = adapter
        self.event_dispatcher = event_dispatcher

    def get_routes(self, path: Optional[str] = None) -> List[tuple]:
        """
        Get routes that this service wants to register with the FastAPI app.

        This method returns a list of tuples with the following structure:
        (path, methods, handler, kwargs) where:
        - path is the URL path for the endpoint
        - methods is a list of HTTP methods this endpoint supports
        - handler is the function to be called when the endpoint is accessed
        - kwargs are additional arguments to pass to the add_api_route method

        Args:
            path: Optional base path to prefix all routes

        Returns:
            List of route tuples (path, methods, handler, kwargs)
        """
        # Default implementation returns empty list
        # Specific service classes should override this
        return []

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata for this service, including capabilities and configuration.

        Returns:
            Dictionary of service metadata
        """
        # Default implementation returns basic info
        # Specific service classes should override this
        return {
            "service_type": self.__class__.__name__,
            "adapter_type": self.adapter.__class__.__name__,
            "operations": self.adapter.get_capabilities()
            if hasattr(self.adapter, "get_capabilities")
            else [],
        }

    @classmethod
    def create(
        cls, adapter_class: Optional[Type[StandardAdapter]] = None, **options
    ) -> "BaseService":
        """
        Factory method to create a new service with default adapter.

        Args:
            adapter_class: The adapter class to use (must be specified if not using default)
            **options: Options to pass to the adapter constructor

        Returns:
            New service instance with configured adapter
        """
        if adapter_class is None:
            raise ValueError("adapter_class must be specified")
        adapter = adapter_class.create(**options)
        return cls(adapter=adapter)
