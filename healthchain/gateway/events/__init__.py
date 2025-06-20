"""
Event handling system for the HealthChain Gateway.

This module provides event dispatching and handling functionality for
asynchronous communication between healthcare systems.
"""

from .dispatcher import EventDispatcher, EHREvent, EHREventType

__all__ = [
    "EventDispatcher",
    "EHREvent",
    "EHREventType",
]
