import asyncio

from enum import Enum
from pydantic import BaseModel
from typing import Dict, List, Callable, Any
from datetime import datetime


class EHREventType(Enum):
    PATIENT_ADMISSION = "patient.admission"
    PATIENT_DISCHARGE = "patient.discharge"
    MEDICATION_ORDER = "medication.order"
    LAB_RESULT = "lab.result"
    APPOINTMENT_SCHEDULE = "appointment.schedule"


class EHREvent(BaseModel):
    event_type: EHREventType
    source_system: str
    timestamp: datetime
    payload: Dict
    metadata: Dict


class EventDispatcher:
    """Dispatches incoming EHR events to registered handlers"""

    def __init__(self):
        self._handlers: Dict[EHREventType, List[Callable]] = {
            event_type: [] for event_type in EHREventType
        }
        self._default_handlers: List[Callable] = []

    def register_handler(
        self, event_type: EHREventType, handler: Callable
    ) -> "EventDispatcher":
        """Register a handler for a specific event type"""
        self._handlers[event_type].append(handler)
        return self

    def register_default_handler(self, handler: Callable) -> "EventDispatcher":
        """Register a handler for all event types"""
        self._default_handlers.append(handler)
        return self

    async def dispatch_event(self, event: EHREvent) -> List[Any]:
        """
        Dispatch event to all registered handlers

        Args:
            event: The event to dispatch

        Returns:
            List of results from all handlers
        """
        handlers = self._handlers[event.event_type] + self._default_handlers

        if not handlers:
            return []

        tasks = [handler(event) for handler in handlers]
        return await asyncio.gather(*tasks)
