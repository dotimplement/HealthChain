"""
API module for HealthChain Gateway.

This module provides the FastAPI application wrapper and dependency injection
for healthcare integrations.
"""

from healthchain.gateway.api.app import HealthChainAPI
from healthchain.gateway.api.dependencies import (
    get_app,
    get_event_dispatcher,
    get_gateway,
    get_all_gateways,
    get_service,
    get_all_services,
    get_gateway_by_name,
    get_service_by_name,
)
from healthchain.gateway.api.protocols import (
    HealthChainAPIProtocol,
    EventDispatcherProtocol,
    FHIRConnectionManagerProtocol,
)

__all__ = [
    "HealthChainAPI",
    "get_app",
    "get_event_dispatcher",
    "get_gateway",
    "get_all_gateways",
    "get_service",
    "get_all_services",
    "get_gateway_by_name",
    "get_service_by_name",
    "HealthChainAPIProtocol",
    "EventDispatcherProtocol",
    "FHIRConnectionManagerProtocol",
]
