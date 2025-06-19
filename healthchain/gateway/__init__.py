"""
HealthChain Gateway Module.

This module provides a secure gateway layer that manages routing, transformation,
and event handling between healthcare systems (FHIR servers, EHRs) with a focus on
maintainable, compliant integration patterns.

Core components:
- BaseGateway: Abstract base class for all gateway implementations
- Protocol implementations: Concrete gateways for various healthcare protocols
- Event system: Publish-subscribe framework for healthcare events
- API framework: FastAPI-based application for exposing gateway endpoints
"""

# Main application exports
from healthchain.gateway.api.app import HealthChainAPI, create_app
from healthchain.gateway.core.fhirgateway import FHIRGateway

# Core components
from healthchain.gateway.core.base import (
    BaseGateway,
    GatewayConfig,
    EventCapability,
)

# Event system
from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREvent,
    EHREventType,
)

# Re-export gateway implementations
from healthchain.gateway.protocols import (
    CDSHooksService,
    NoteReaderService,
)

__all__ = [
    # API
    "HealthChainAPI",
    "create_app",
    # Core
    "BaseGateway",
    "GatewayConfig",
    "EventCapability",
    # Events
    "EventDispatcher",
    "EHREvent",
    "EHREventType",
    # Gateways
    "FHIRGateway",
    # Services
    "CDSHooksService",
    "NoteReaderService",
]
