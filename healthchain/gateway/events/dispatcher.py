from enum import Enum
from pydantic import BaseModel
from typing import Dict
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
    """Event dispatcher for handling EHR system events.

    This class provides a mechanism to register and dispatch event handlers for different
    types of EHR events. It supports both type-specific handlers and default handlers
    that process all event types.

    Example:
        ```python
        dispatcher = EventDispatcher()

        @dispatcher.register_handler(EHREventType.PATIENT_ADMISSION)
        async def handle_admission(event):
            # Process admission event
            pass

        @dispatcher.register_default_handler
        async def log_all_events(event):
            # Log all events
            pass
        ```
    """

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, handler):
        """Subscribe to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    async def publish(self, event):
        """Publish an event to all subscribers."""
        event_type = event.event_type
        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                await handler(event)
