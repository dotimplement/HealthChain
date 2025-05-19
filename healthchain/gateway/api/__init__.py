"""
HealthChain API module.

This module provides API components for the HealthChain gateway.
"""

from healthchain.gateway.api.app import HealthChainAPI, create_app
from healthchain.gateway.api.dependencies import (
    get_app,
    get_event_dispatcher,
    get_gateway,
    get_all_gateways,
    get_typed_gateway,
)
from healthchain.gateway.api.protocols import (
    HealthChainAPIProtocol,
    GatewayProtocol,
    EventDispatcherProtocol,
    FHIRGatewayProtocol,
    SOAPGatewayProtocol,
)

__all__ = [
    # Classes
    "HealthChainAPI",
    # Functions
    "create_app",
    "get_app",
    "get_event_dispatcher",
    "get_gateway",
    "get_all_gateways",
    "get_typed_gateway",
    # Protocols
    "HealthChainAPIProtocol",
    "GatewayProtocol",
    "EventDispatcherProtocol",
    "FHIRGatewayProtocol",
    "SOAPGatewayProtocol",
]
