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


class EventDispatcherMixin:
    """
    Mixin class that provides event dispatching capabilities.

    This mixin encapsulates all event-related functionality to allow for cleaner separation
    of concerns and optional event support in gateways.
    """

    def __init__(self):
        """
        Initialize event dispatching capabilities.
        """
        self.event_dispatcher = None
        self._event_creator = None

    def _run_async_publish(self, event):
        """
        Safely run the async publish method in a way that works in both sync and async contexts.

        Args:
            event: The event to publish
        """
        if not self.event_dispatcher:
            return

        try:
            # Try to get the running loop (only works in async context)
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, so create_task works
                asyncio.create_task(self.event_dispatcher.publish(event))
            except RuntimeError:
                # We're not in an async context, create a new loop
                loop = asyncio.new_event_loop()
                try:
                    # Run the coroutine to completion in the new loop
                    loop.run_until_complete(self.event_dispatcher.publish(event))
                finally:
                    # Clean up the loop
                    loop.close()
        except Exception as e:
            logger.error(f"Failed to publish event: {str(e)}", exc_info=True)

    def set_event_dispatcher(self, dispatcher):
        """
        Set the event dispatcher for this gateway.

        This allows the gateway to publish events and register handlers.

        Args:
            dispatcher: The event dispatcher instance

        Returns:
            Self, to allow for method chaining
        """
        self.event_dispatcher = dispatcher

        # Register default handlers
        self._register_default_handlers()

        return self

    def set_event_creator(self, creator_function: Callable):
        """
        Set a custom function to map gateway-specific events to EHREvents.

        The creator function will be called instead of any default event creation logic,
        allowing users to define custom event creation without subclassing.

        Args:
            creator_function: Function that accepts gateway-specific arguments
                             and returns an EHREvent or None

        Returns:
            Self, to allow for method chaining
        """
        self._event_creator = creator_function
        return self

    def _register_default_handlers(self):
        """
        Register default event handlers for this gateway.

        Override this method in subclasses to register default handlers
        for specific event types relevant to the gateway.
        """
        # Base implementation does nothing
        # Subclasses should override this method to register their default handlers
        pass

    def register_event_handler(self, event_type, handler=None):
        """
        Register a custom event handler for a specific event type.

        This can be used as a decorator or called directly.

        Args:
            event_type: The type of event to handle
            handler: The handler function (optional if used as decorator)

        Returns:
            Decorator function if handler is None, self otherwise
        """
        if not self.event_dispatcher:
            raise ValueError("Event dispatcher not set for this gateway")

        # If used as a decorator (no handler provided)
        if handler is None:
            return self.event_dispatcher.register_handler(event_type)

        # If called directly with a handler
        self.event_dispatcher.register_handler(event_type)(handler)
        return self


class BaseProtocolHandler(ABC, Generic[T, R], EventDispatcherMixin):
    """
    Base class for protocol handlers that process specific request/response types.

    This is designed for CDS Hooks, SOAP, and other protocol-specific handlers that:
    - Have a specific request/response type
    - Use decorator pattern for handler registration
    - Process operations through registered handlers

    Type Parameters:
        T: The request type this handler processes
        R: The response type this handler returns
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

        # Initialize event dispatcher mixin
        EventDispatcherMixin.__init__(self)

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


class BaseGateway(ABC, APIRouter, EventDispatcherMixin):
    """
    Base class for healthcare integration gateways.

    Combines FastAPI routing capabilities with event
    dispatching to enable protocol-specific integrations.
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

        # Initialize event dispatcher mixin
        EventDispatcherMixin.__init__(self)

    # TODO: Implement this
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata for this gateway, including capabilities and configuration.

        Returns:
            Dictionary of gateway metadata
        """
        # Default implementation returns basic info
        # Specific gateway classes should override this
        metadata = {
            "gateway_type": self.__class__.__name__,
            "system_type": self.config.system_type,
        }

        # Add event-related metadata if events are enabled
        if self.event_dispatcher:
            metadata["event_enabled"] = True

        return metadata
