"""
Base classes for the HealthChain Gateway.

This module provides the core abstract base classes that define the
architecture of the gateway system.
"""

import logging
import asyncio

from abc import ABC
from typing import Any, Callable, Dict, List, TypeVar, Generic, Optional, Union
from pydantic import BaseModel
from fastapi import APIRouter

from healthchain.gateway.api.protocols import EventDispatcherProtocol


logger = logging.getLogger(__name__)


# Type variables for self-referencing return types and generic gateways
G = TypeVar("G", bound="BaseGateway")
P = TypeVar("P", bound="BaseProtocolHandler")
T = TypeVar("T")  # For generic request types
R = TypeVar("R")  # For generic response types


class GatewayConfig(BaseModel):
    """Base configuration class for gateways"""

    return_errors: bool = False
    system_type: str = "GENERIC"


class EventCapability:
    """
    Encapsulates event dispatching functionality.

    """

    def __init__(self):
        """Initialize event dispatching capabilities."""
        self.dispatcher: Optional[EventDispatcherProtocol] = (
            None  # EventDispatcherProtocol
        )
        self._event_creator: Optional[Callable] = None

    def publish(self, event):
        """
        Publish an event using the configured dispatcher.

        Args:
            event: The event to publish
        """
        if not self.dispatcher:
            return

        # Delegate to dispatcher's sync-friendly publish method
        self.dispatcher.emit(event)

    def set_dispatcher(self, dispatcher) -> "EventCapability":
        """
        Set the event dispatcher.

        Args:
            dispatcher: The event dispatcher instance

        Returns:
            Self, to allow for method chaining
        """
        self.dispatcher = dispatcher
        return self

    def set_event_creator(self, creator_function: Callable) -> "EventCapability":
        """
        Set a custom function to map gateway-specific events to EHREvents.

        Args:
            creator_function: Function that accepts gateway-specific arguments
                             and returns an EHREvent or None

        Returns:
            Self, to allow for method chaining
        """
        self._event_creator = creator_function
        return self

    def register_handler(self, event_type, handler=None):
        """
        Register a custom event handler for a specific event type.

        This can be used as a decorator or called directly.

        Args:
            event_type: The type of event to handle
            handler: The handler function (optional if used as decorator)

        Returns:
            Decorator function if handler is None, the capability object otherwise
        """
        if not self.dispatcher:
            raise ValueError("Event dispatcher not set")

        # If used as a decorator (no handler provided)
        if handler is None:
            return self.dispatcher.register_handler(event_type)

        # If called directly with a handler
        self.dispatcher.register_handler(event_type)(handler)
        return self

    def emit_event(
        self, creator_function: Callable, *args, use_events: bool = True, **kwargs
    ) -> None:
        """
        Emit an event using the standard custom/fallback pattern.

        This method implements the common event emission pattern used across
        all protocol handlers: try custom event creator first, then fallback
        to standard event creator.

        Args:
            creator_function: Standard event creator function to use as fallback
            *args: Positional arguments to pass to the event creator
            use_events: Whether events are enabled for this operation
            **kwargs: Keyword arguments to pass to the event creator

        Example:
            # In a protocol handler
            self.events.emit_event(
                create_fhir_event,
                operation, resource_type, resource_id, resource
            )
        """
        # Skip if events are disabled or no dispatcher
        if not self.dispatcher or not use_events:
            return

        # Use custom event creator if provided
        if self._event_creator:
            event = self._event_creator(*args)
            if event:
                self.publish(event)
            return

        # Create a standard event using the provided creator function
        event = creator_function(*args, **kwargs)
        if event:
            self.publish(event)


class BaseProtocolHandler(ABC, Generic[T, R]):
    """
    Base class for protocol handlers that process specific request/response types.

    This is designed for CDS Hooks, SOAP, and other protocol-specific handlers.
    Register handlers with the register_handler method.
    """

    def __init__(
        self, config: Optional[GatewayConfig] = None, use_events: bool = True, **options
    ):
        """
        Initialize a new protocol handler.

        Args:
            config: Configuration options for the handler
            use_events: Whether to enable event dispatching
            **options: Additional configuration options
        """
        self._handlers = {}
        self.options = options
        self.config = config or GatewayConfig()
        self.use_events = use_events
        # Default to raising exceptions unless configured otherwise
        self.return_errors = self.config.return_errors or options.get(
            "return_errors", False
        )
        self.events = EventCapability()

    def register_handler(self, operation: str, handler: Callable) -> P:
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

    def get_capabilities(self) -> List[str]:
        """
        Get list of operations this handler supports.

        Returns:
            List of supported operation names
        """
        return list(self._handlers.keys())

    @classmethod
    def create(cls, **options) -> G:
        """
        Factory method to create a new gateway with default configuration.

        Args:
            **options: Options to pass to the constructor

        Returns:
            New gateway instance
        """
        return cls(**options)


class BaseGateway(ABC, APIRouter):
    """
    Base class for healthcare integration gateways.

    Combines FastAPI routing capabilities with event dispatching using composition.
    """

    def __init__(
        self,
        config: Optional[GatewayConfig] = None,
        use_events: bool = True,
        prefix: str = "/api",
        tags: Optional[List[str]] = None,
        **options,
    ):
        """
        Initialize a new gateway.

        Args:
            config: Configuration options for the gateway
            use_events: Whether to enable event dispatching
            prefix: URL prefix for API routes
            tags: OpenAPI tags
            **options: Additional configuration options
        """
        # Initialize APIRouter
        APIRouter.__init__(self, prefix=prefix, tags=tags or [])

        self.options = options
        self.config = config or GatewayConfig()
        self.use_events = use_events
        # Default to raising exceptions unless configured otherwise
        self.return_errors = self.config.return_errors or options.get(
            "return_errors", False
        )
        self.events = EventCapability() if self.use_events else None

    def get_gateway_status(self) -> Dict[str, Any]:
        """
        Get operational status and metadata for this gateway.

        Returns:
            Dictionary of gateway operational status and metadata
        """
        # Default implementation returns basic info
        # Specific gateway classes should override this
        status = {
            "gateway_type": self.__class__.__name__,
            "system_type": self.config.system_type,
            "status": "active",
            "return_errors": self.return_errors,
        }

        # Add event-related metadata if events are enabled
        if self.use_events:
            status["events"] = {
                "enabled": True,
                "dispatcher_configured": self.events.dispatcher is not None,
            }

        return status
