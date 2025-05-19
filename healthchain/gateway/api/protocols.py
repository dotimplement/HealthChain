"""
Protocol definitions for the HealthChain gateway system.

This module defines Protocol classes that specify the interfaces
for various components of the gateway system, enabling structural
typing and better type checking.
"""

from typing import Dict, Optional, Set, Any, Protocol, Callable, Union

from healthchain.gateway.events.dispatcher import EHREvent


class EventDispatcherProtocol(Protocol):
    """Protocol defining the interface for event dispatchers."""

    async def publish(
        self, event: EHREvent, middleware_id: Optional[int] = None
    ) -> bool:
        """Dispatch an event to registered handlers.

        Args:
            event: The event to publish
            middleware_id: Optional middleware ID

        Returns:
            True if the event was successfully dispatched
        """
        ...

    def init_app(self, app: Any) -> None:
        """Initialize the dispatcher with an application.

        Args:
            app: Application instance to initialize with
        """
        ...

    def register_handler(self, event_name: str, handler: Callable) -> None:
        """Register a handler for a specific event.

        Args:
            event_name: The name of the event to handle
            handler: The handler function
        """
        ...


class GatewayProtocol(Protocol):
    """Protocol defining the interface for gateways."""

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the gateway.

        Returns:
            Dictionary with gateway metadata
        """
        ...

    def set_event_dispatcher(self, dispatcher: EventDispatcherProtocol) -> None:
        """Set the event dispatcher for this gateway.

        Args:
            dispatcher: The event dispatcher to use
        """
        ...


class FHIRGatewayProtocol(GatewayProtocol, Protocol):
    """Protocol defining the interface for FHIR gateways."""

    async def search(
        self, resource_type: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search for FHIR resources.

        Args:
            resource_type: The FHIR resource type
            params: Search parameters

        Returns:
            FHIR Bundle containing search results
        """
        ...

    async def read(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Read a FHIR resource.

        Args:
            resource_type: The FHIR resource type
            resource_id: The resource ID

        Returns:
            FHIR resource
        """
        ...


class SOAPGatewayProtocol(GatewayProtocol, Protocol):
    """Protocol defining the interface for SOAP gateways."""

    def create_wsgi_app(self) -> Any:
        """Create a WSGI application for the SOAP service.

        Returns:
            WSGI application
        """
        ...

    def register_method(self, method_name: str, handler: Callable) -> None:
        """Register a method handler for the SOAP service.

        Args:
            method_name: The SOAP method name
            handler: The handler function
        """
        ...


class HealthChainAPIProtocol(Protocol):
    """Protocol defining the interface for the HealthChainAPI."""

    gateways: Dict[str, GatewayProtocol]
    gateway_endpoints: Dict[str, Set[str]]
    enable_events: bool
    event_dispatcher: Optional[EventDispatcherProtocol]

    def get_event_dispatcher(self) -> Optional[EventDispatcherProtocol]:
        """Get the event dispatcher.

        Returns:
            The event dispatcher or None if events are disabled
        """
        ...

    def get_gateway(self, gateway_name: str) -> Optional[GatewayProtocol]:
        """Get a gateway by name.

        Args:
            gateway_name: The name of the gateway

        Returns:
            The gateway or None if not found
        """
        ...

    def get_all_gateways(self) -> Dict[str, GatewayProtocol]:
        """Get all registered gateways.

        Returns:
            Dictionary of all registered gateways
        """
        ...

    def register_gateway(
        self,
        gateway: Union[GatewayProtocol, Any],
        path: Optional[str] = None,
        use_events: Optional[bool] = None,
        **options,
    ) -> None:
        """Register a gateway.

        Args:
            gateway: The gateway to register
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
