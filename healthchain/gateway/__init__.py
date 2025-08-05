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
from healthchain.gateway.base import BaseGateway, BaseProtocolHandler
from healthchain.gateway.fhir.sync import FHIRGateway
from healthchain.gateway.fhir.aio import AsyncFHIRGateway

# Protocol Handlers
from healthchain.gateway.cds import CDSHooksService
from healthchain.gateway.soap.notereader import NoteReaderService

# Event System
from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREvent,
    EHREventType,
)

# Client Utilities
from healthchain.gateway.clients.pool import ClientPool
from healthchain.gateway.clients.fhir.aio import AsyncFHIRClient
from healthchain.gateway.clients.fhir.sync import FHIRClient

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
    "AsyncFHIRGateway",
    # Protocols
    "CDSHooksService",
    "NoteReaderService",
    # Events
    "EventDispatcher",
    "EHREvent",
    "EHREventType",
    # Clients
    "AsyncFHIRClient",
    "FHIRClient",
    "ClientPool",
]
