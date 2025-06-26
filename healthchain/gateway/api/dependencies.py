"""
Dependency providers for HealthChainAPI.

This module contains dependency functions that can be
used in route handlers to access HealthChainAPI components.
"""

from fastapi import Depends, HTTPException
from typing import Dict, Optional, Any

from healthchain.gateway.api.protocols import (
    HealthChainAPIProtocol,
    EventDispatcherProtocol,
)


def get_app() -> HealthChainAPIProtocol:
    """Get the current HealthChainAPI application instance.

    This is a placeholder that should be overridden by the actual
    HealthChainAPI instance through dependency_overrides.

    Returns:
        The HealthChainAPI instance
    """
    raise RuntimeError("HealthChainAPI instance not available")


def get_event_dispatcher(
    app: HealthChainAPIProtocol = Depends(get_app),
) -> Optional[EventDispatcherProtocol]:
    """Get the event dispatcher from the current application.

    Args:
        app: The HealthChainAPI instance

    Returns:
        The event dispatcher or None if events are disabled
    """
    return app.get_event_dispatcher()


def get_gateway(
    gateway_name: str, app: HealthChainAPIProtocol = Depends(get_app)
) -> Optional[Any]:
    """Get a specific gateway by name.

    Args:
        gateway_name: The name of the gateway to retrieve
        app: The HealthChainAPI instance

    Returns:
        The gateway instance or None if not found
    """
    return app.gateways.get(gateway_name)


def get_all_gateways(
    app: HealthChainAPIProtocol = Depends(get_app),
) -> Dict[str, Any]:
    """Get all registered gateways.

    Args:
        app: The HealthChainAPI instance

    Returns:
        Dictionary of all registered gateways
    """
    return app.gateways


def get_service(
    service_name: str, app: HealthChainAPIProtocol = Depends(get_app)
) -> Optional[Any]:
    """Get a specific service by name.

    Args:
        service_name: The name of the service to retrieve
        app: The HealthChainAPI instance

    Returns:
        The service instance or None if not found
    """
    return app.services.get(service_name)


def get_all_services(
    app: HealthChainAPIProtocol = Depends(get_app),
) -> Dict[str, Any]:
    """Get all registered services.

    Args:
        app: The HealthChainAPI instance

    Returns:
        Dictionary of all registered services
    """
    return app.services


def get_gateway_by_name(gateway_name: str):
    """Dependency factory for getting a specific gateway by name.

    Args:
        gateway_name: The name of the gateway to retrieve

    Returns:
        A dependency function that returns the gateway
    """

    def _get_gateway_dependency(
        app: HealthChainAPIProtocol = Depends(get_app),
    ) -> Any:
        gateway = app.gateways.get(gateway_name)
        if gateway is None:
            raise HTTPException(
                status_code=404, detail=f"Gateway '{gateway_name}' not found"
            )
        return gateway

    return _get_gateway_dependency


def get_service_by_name(service_name: str):
    """Dependency factory for getting a specific service by name.

    Args:
        service_name: The name of the service to retrieve

    Returns:
        A dependency function that returns the service
    """

    def _get_service_dependency(
        app: HealthChainAPIProtocol = Depends(get_app),
    ) -> Any:
        service = app.services.get(service_name)
        if service is None:
            raise HTTPException(
                status_code=404, detail=f"Service '{service_name}' not found"
            )
        return service

    return _get_service_dependency
