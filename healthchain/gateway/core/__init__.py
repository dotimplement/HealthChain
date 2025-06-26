"""
Core components for the HealthChain Gateway module.

This module contains the base abstractions and core components
that define the gateway architecture.
"""

from .base import BaseGateway, GatewayConfig, EventCapability
from .connection import FHIRConnectionManager
from .errors import FHIRErrorHandler, FHIRConnectionError
from .fhirgateway import FHIRGateway

# Import these if available, but don't error if they're not
try:
    __all__ = [
        "BaseGateway",
        "GatewayConfig",
        "EventCapability",
        "FHIRConnectionManager",
        "FHIRErrorHandler",
        "FHIRConnectionError",
        "FHIRGateway",
        "EHREvent",
        "SOAPEvent",
        "EHREventType",
        "RequestModel",
        "ResponseModel",
    ]
except ImportError:
    __all__ = [
        "BaseGateway",
        "GatewayConfig",
        "EventCapability",
        "FHIRConnectionManager",
        "FHIRErrorHandler",
        "FHIRConnectionError",
        "FHIRGateway",
    ]
