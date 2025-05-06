"""
Event handling system for the HealthChain Gateway.

This module provides event dispatching and handling functionality for
asynchronous communication between healthcare systems.
"""

from .dispatcher import EventDispatcher, EHREvent, EHREventType
from .ehr import EHREventPublisher
from .soap import SOAPEvent, SOAPEventPublisher

__all__ = [
    "EventDispatcher",
    "EHREvent",
    "EHREventType",
    "EHREventPublisher",
    "SOAPEvent",
    "SOAPEventPublisher",
]
