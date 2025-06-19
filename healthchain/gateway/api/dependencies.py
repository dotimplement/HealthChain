"""
Dependency providers for HealthChainAPI.

This module contains FastAPI dependency injection providers that can be
used in route handlers to access HealthChainAPI components.
"""

from typing import Dict, Optional, TypeVar, cast, Callable
from fastapi import Depends

from healthchain.gateway.api.protocols import (
    HealthChainAPIProtocol,
    EventDispatcherProtocol,
)
from healthchain.gateway.core.base import BaseGateway

# Type variable for type hinting
T = TypeVar("T", bound=BaseGateway)


# Application instance dependency
def get_app() -> HealthChainAPIProtocol:
    """Get the current HealthChainAPI application instance.

    This is a dependency that returns the current application instance.
    It should be overridden during application startup.

    Returns:
        The HealthChainAPI instance
    """
    raise RuntimeError(
        "get_app dependency has not been overridden. "
        "This usually happens when you try to use the dependency outside "
        "of a request context or before the application has been initialized."
    )


def get_event_dispatcher(
    app: HealthChainAPIProtocol = Depends(get_app),
) -> Optional[EventDispatcherProtocol]:
    """Get the event dispatcher from the app.

    This is a dependency that can be used in route handlers to access
    the event dispatcher.

    Args:
        app: The HealthChainAPI instance

    Returns:
        The event dispatcher or None if events are disabled
    """
    return app.get_event_dispatcher()


def get_gateway(
    gateway_name: str, app: HealthChainAPIProtocol = Depends(get_app)
) -> Optional[BaseGateway]:
    """Get a specific gateway from the app.

    This is a dependency that can be used in route handlers to access
    a specific gateway.

    Args:
        gateway_name: The name of the gateway to retrieve
        app: The HealthChainAPI instance

    Returns:
        The gateway or None if not found
    """
    return app.get_gateway(gateway_name)


def get_all_gateways(
    app: HealthChainAPIProtocol = Depends(get_app),
) -> Dict[str, BaseGateway]:
    """Get all registered gateways from the app.

    This is a dependency that can be used in route handlers to access
    all gateways.

    Args:
        app: The HealthChainAPI instance

    Returns:
        Dictionary of all registered gateways
    """
    return app.get_all_gateways()


def get_typed_gateway(
    gateway_name: str, gateway_type: type[T]
) -> Callable[[], Optional[T]]:
    """Create a dependency that returns a gateway of a specific type.

    This creates a dependency that returns a gateway cast to a specific type,
    which is useful when you need a specific gateway protocol.

    Args:
        gateway_name: Name of the gateway to retrieve
        gateway_type: The expected gateway type/protocol

    Returns:
        A dependency function that returns the typed gateway
    """

    def _get_typed_gateway(
        app: HealthChainAPIProtocol = Depends(get_app),
    ) -> Optional[T]:  # type: ignore
        gateway = app.get_gateway(gateway_name)
        if gateway is None:
            return None
        return cast(T, gateway)

    return _get_typed_gateway
