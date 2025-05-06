"""
HealthChain Gateway Module

A secure gateway layer that manages routing, transformation, and event handling
between healthcare systems with a focus on maintainable, compliant integration patterns.
"""

# Core components
from healthchain.gateway.core.base import ProtocolService, ClientConnector
from healthchain.gateway.core.manager import GatewayManager

# Protocol services (inbound)
from healthchain.gateway.protocols.cdshooks import CDSHooksService
from healthchain.gateway.protocols.soap import SOAPService

# Client connectors (outbound)
from healthchain.gateway.clients.fhir import FHIRClient

# Event dispatcher
from healthchain.gateway.events.ehr import EHREventPublisher
from healthchain.gateway.events.soap import SOAPEventPublisher
from healthchain.gateway.events.dispatcher import EventDispatcher

# Security
from healthchain.gateway.security import SecurityProxy

__all__ = [
    # Core classes
    "ProtocolService",
    "ClientConnector",
    "GatewayManager",
    # Protocol services
    "CDSHooksService",
    "SOAPService",
    # Client connectors
    "FHIRClient",
    # Event dispatcher
    "EHREventPublisher",
    "SOAPEventPublisher",
    "EventDispatcher",
    # Security
    "SecurityProxy",
]
