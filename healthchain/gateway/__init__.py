"""
HealthChain Gateway Module.

This module provides the core gateway functionality for HealthChain,
including API applications, protocol handlers, and healthcare integrations.
"""

# API Components
from healthchain.gateway.api.app import HealthChainAPI
from healthchain.gateway.api.dependencies import (
    get_app,
    get_event_dispatcher,
    get_gateway,
    get_all_gateways,
)

# Core Components
from healthchain.gateway.core.base import BaseGateway, BaseProtocolHandler
from healthchain.gateway.core.fhirgateway import FHIRGateway

# Protocol Handlers
from healthchain.gateway.protocols.cdshooks import CDSHooksService
from healthchain.gateway.protocols.notereader import NoteReaderService

# Event System
from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREvent,
    EHREventType,
)

# Client Utilities
from healthchain.gateway.clients.fhir import AsyncFHIRClient
from healthchain.gateway.clients.pool import FHIRClientPool

__all__ = [
    # API
    "HealthChainAPI",
    "get_app",
    "get_event_dispatcher",
    "get_gateway",
    "get_all_gateways",
    # Core
    "BaseGateway",
    "BaseProtocolHandler",
    "FHIRGateway",
    # Protocols
    "CDSHooksService",
    "NoteReaderService",
    # Events
    "EventDispatcher",
    "EHREvent",
    "EHREventType",
    # Clients
    "AsyncFHIRClient",
    "FHIRClientPool",
]
