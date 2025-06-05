"""
Core components for the HealthChain Gateway module.

This module contains the base abstractions and core components
that define the gateway architecture.
"""

from .base import BaseGateway, GatewayConfig

# Import these if available, but don't error if they're not
try:
    __all__ = [
        "BaseGateway",
        "GatewayConfig",
    ]
except ImportError:
    __all__ = [
        "BaseGateway",
        "GatewayConfig",
    ]
