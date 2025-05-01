from typing import Dict
from datetime import datetime

from healthchain.gateway.core.base import BaseGateway
from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREvent,
    EHREventType,
)


class EHREventGateway(BaseGateway):
    """Gateway for handling incoming EHR events"""

    def __init__(self, system_type: str, dispatcher: EventDispatcher):
        self.system_type = system_type
        self.dispatcher = dispatcher

    async def handle_incoming_event(self, raw_event: Dict):
        """Process incoming EHR event"""
        # Validate and parse incoming event
        event = self._parse_event(raw_event)

        # Dispatch to handlers
        await self.dispatcher.dispatch_event(event)

    def _parse_event(self, raw_event: Dict) -> EHREvent:
        """Parse raw event data into EHREvent object"""
        return EHREvent(
            event_type=EHREventType(raw_event["type"]),
            source_system=self.system_type,
            timestamp=datetime.fromisoformat(raw_event["timestamp"]),
            payload=raw_event["payload"],
            metadata=raw_event.get("metadata", {}),
        )
