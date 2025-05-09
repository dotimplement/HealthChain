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
        """Initialize the event dispatcher with empty handler registries."""
        self._handlers: Dict[EHREventType, List[Callable]] = {
            event_type: [] for event_type in EHREventType
        }
        self._default_handlers: List[Callable] = []

    def register_handler(
        self, event_type: EHREventType, handler: Callable
    ) -> "EventDispatcher":
        """Register a handler for a specific event type.

        Args:
            event_type: The type of event this handler will process
            handler: Async callable that takes an EHREvent and returns Any

        Returns:
            Self for method chaining
        """
        self._handlers[event_type].append(handler)
        return self

    def register_default_handler(self, handler: Callable) -> "EventDispatcher":
        """Register a handler that processes all event types.

        Args:
            handler: Async callable that takes an EHREvent and returns Any

        Returns:
            Self for method chaining
        """
        self._default_handlers.append(handler)
        return self

    async def dispatch_event(self, event: EHREvent) -> List[Any]:
        """Dispatch an event to all registered handlers.

        This method will:
        1. Find all handlers registered for the event type
        2. Add any default handlers
        3. Execute all handlers concurrently
        4. Return a list of all handler results

        Args:
            event: The EHR event to dispatch

        Returns:
            List of results from all handlers that processed the event
        """
        handlers = self._handlers[event.event_type] + self._default_handlers

        if not handlers:
            return []

        tasks = [handler(event) for handler in handlers]
        return await asyncio.gather(*tasks)
