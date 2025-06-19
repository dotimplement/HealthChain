"""
Protocol definitions for the HealthChain gateway system.

This module defines Protocol classes that specify the interfaces
for various components of the gateway system, enabling structural
typing and better type checking.
"""

from typing import (
    Dict,
    Optional,
    Set,
    Any,
    Protocol,
    Callable,
    Union,
    Type,
    TYPE_CHECKING,
)

from healthchain.gateway.events.dispatcher import EHREvent, EHREventType

if TYPE_CHECKING:
    from fastapi import FastAPI


class EventDispatcherProtocol(Protocol):
    """Protocol defining the interface for event dispatchers."""

    async def publish(
        self, event: EHREvent, middleware_id: Optional[int] = None
    ) -> None:
        """Dispatch an event to registered handlers.

        Args:
            event: The event to publish
            middleware_id: Optional middleware ID
        """
        ...

    def init_app(self, app: "FastAPI") -> None:
        """Initialize the dispatcher with a FastAPI application.

        Args:
            app: FastAPI application instance to initialize with
        """
        ...

    def register_handler(self, event_type: EHREventType) -> Callable:
        """Register a handler for a specific event type.

        Args:
            event_type: The EHR event type to handle

        Returns:
            Decorator function for registering handlers
        """
        ...

    def register_default_handler(self) -> Callable:
        """Register a handler for all events.

        Returns:
            Decorator function for registering handlers
        """
        ...


class HealthChainAPIProtocol(Protocol):
    """Protocol defining the interface for the HealthChainAPI."""

    gateways: Dict[str, Any]
    services: Dict[str, Any]
    gateway_endpoints: Dict[str, Set[str]]
    service_endpoints: Dict[str, Set[str]]
    enable_events: bool
    event_dispatcher: Optional[EventDispatcherProtocol]

    def get_event_dispatcher(self) -> Optional[EventDispatcherProtocol]:
        """Get the event dispatcher.

        Returns:
            The event dispatcher or None if events are disabled
        """
        ...

    def get_gateway(self, gateway_name: str) -> Optional[Any]:
        """Get a gateway by name.

        Args:
            gateway_name: The name of the gateway

        Returns:
            The gateway or None if not found
        """
        ...

    def get_all_gateways(self) -> Dict[str, Any]:
        """Get all registered gateways.

        Returns:
            Dictionary of all registered gateways
        """
        ...

    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service by name.

        Args:
            service_name: The name of the service

        Returns:
            The service or None if not found
        """
        ...

    def get_all_services(self) -> Dict[str, Any]:
        """Get all registered services.

        Returns:
            Dictionary of all registered services
        """
        ...

    def register_gateway(
        self,
        gateway: Union[Type[Any], Any],
        path: Optional[str] = None,
        use_events: Optional[bool] = None,
        **options,
    ) -> None:
        """Register a gateway.

        Args:
            gateway: The gateway to register (class or instance)
            path: Optional mount path
            use_events: Whether to use events
            **options: Additional options
        """
        ...

    def register_service(
        self,
        service: Union[Type[Any], Any],
        path: Optional[str] = None,
        use_events: Optional[bool] = None,
        **options,
    ) -> None:
        """Register a service.

        Args:
            service: The service to register (class or instance)
            path: Optional mount path
            use_events: Whether to use events
            **options: Additional options
        """
        ...

    def register_router(self, router: Any, **options) -> None:
        """Register a router.

        Args:
            router: The router to register
            **options: Additional options
        """
        ...


class FHIRConnectionManagerProtocol(Protocol):
    """Protocol for FHIR connection management."""

    def add_source(self, name: str, connection_string: str) -> None:
        """Add a FHIR data source."""
        ...

    async def get_client(self, source: str = None) -> "FHIRServerInterfaceProtocol":
        """Get a FHIR client for the specified source."""
        ...

    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        ...

    async def close(self) -> None:
        """Close all connections."""
        ...

    @property
    def sources(self) -> Dict[str, Any]:
        """Get registered sources."""
        ...


class FHIRServerInterfaceProtocol(Protocol):
    """Protocol for FHIR server interface."""

    async def read(self, resource_type: Type[Any], resource_id: str) -> Any:
        """Read a FHIR resource."""
        ...

    async def search(
        self, resource_type: Type[Any], params: Dict[str, Any] = None
    ) -> Any:
        """Search for FHIR resources."""
        ...

    async def create(self, resource: Any) -> Any:
        """Create a FHIR resource."""
        ...

    async def update(self, resource: Any) -> Any:
        """Update a FHIR resource."""
        ...

    async def delete(self, resource_type: Type[Any], resource_id: str) -> bool:
        """Delete a FHIR resource."""
        ...

    async def transaction(self, bundle: Any) -> Any:
        """Execute a transaction bundle."""
        ...

    async def capabilities(self) -> Any:
        """Get server capabilities."""
        ...


class FHIRClientPoolProtocol(Protocol):
    """Protocol for FHIR client pooling."""

    async def get_client(self, connection_string: str) -> FHIRServerInterfaceProtocol:
        """Get a client for the given connection string."""
        ...

    async def close(self) -> None:
        """Close all clients in the pool."""
        ...

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        ...
