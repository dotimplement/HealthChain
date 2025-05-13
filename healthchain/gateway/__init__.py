"""
HealthChain Gateway Module

A secure gateway layer that manages routing, transformation, and event handling
between healthcare systems with a focus on maintainable, compliant integration patterns.
"""

# Core components
from .core.base import (
    StandardAdapter,
    InboundAdapter,
    OutboundAdapter,
)

# Protocol services (inbound)
from .services.cdshooks import CDSHooksService
from .services.notereader import NoteReaderService

# Client connectors (outbound)
from .core.fhir_gateway import FHIRGateway

# Event dispatcher
from .events.dispatcher import EventDispatcher

# Security
from .security import SecurityProxy

__all__ = [
    # Core classes
    "StandardAdapter",
    "InboundAdapter",
    "OutboundAdapter",
    "FHIRGateway",
    # Protocol services
    "CDSHooksService",
    "NoteReaderService",
    # Event dispatcher
    "EventDispatcher",
    # Security
    "SecurityProxy",
]
