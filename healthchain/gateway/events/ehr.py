from typing import Dict, Any
from datetime import datetime

from healthchain.gateway.core.base import ProtocolService
from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREvent,
    EHREventType,
)


class EHREventPublisher(ProtocolService):
    """Service for handling incoming EHR events"""

    def __init__(self, system_type: str, dispatcher: EventDispatcher = None, **options):
        super().__init__(**options)
        self.system_type = system_type
        self.dispatcher = dispatcher or EventDispatcher()

        # Register default handlers
        self.register_handler("incoming_event", self.handle_incoming_event)

    async def handle_incoming_event(self, raw_event: Dict) -> Dict[str, Any]:
        """Process incoming EHR event"""
        # Validate and parse incoming event
        event = self._parse_event(raw_event)

        # Dispatch to handlers
        results = await self.dispatcher.dispatch_event(event)

        return {
            "status": "success",
            "event_id": str(event.timestamp),
            "handlers_executed": len(results),
        }

    def _parse_event(self, raw_event: Dict) -> EHREvent:
        """Parse raw event data into EHREvent object"""
        return EHREvent(
            event_type=EHREventType(raw_event["type"]),
            source_system=self.system_type,
            timestamp=datetime.fromisoformat(
                raw_event.get("timestamp", datetime.now().isoformat())
            ),
            payload=raw_event["payload"],
            metadata=raw_event.get("metadata", {}),
        )

    def event_handler(self, event_type: EHREventType):
        """
        Decorator to register event handlers

        Args:
            event_type: The type of event to handle

        Returns:
            Decorator function
        """

        def decorator(handler):
            self.dispatcher.register_handler(event_type, handler)
            return handler

        return decorator
