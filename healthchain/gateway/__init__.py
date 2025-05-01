"""
HealthChain Gateway Module

A secure gateway layer that manages routing, transformation, and event handling
between healthcare systems with a focus on maintainable, compliant integration patterns.
"""

# Core components
from .core.base import BaseGateway, ProtocolHandler
from .core.manager import GatewayManager

# Security
from .security.proxy import SecurityProxy

# API
from .api import create_app

# Protocols
from .protocols.fhir import FhirAPIGateway

# Events
from .events.dispatcher import EventDispatcher, EHREventType
from .events.ehr import EHREvent, EHREventGateway
from .events.soap import SOAPEvent, SOAPEventGateway

__all__ = [
    "create_app",
    "BaseGateway",
    "ProtocolHandler",
    "GatewayManager",
    "SecurityProxy",
    "EventDispatcher",
    "EHREventType",
    "EHREvent",
    "EHREventGateway",
    "SOAPEvent",
    "SOAPEventGateway",
    "FhirAPIGateway",
]
