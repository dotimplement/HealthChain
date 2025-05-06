from datetime import datetime
from typing import Dict, Any

from pydantic import Field
from healthchain.gateway.core.base import ProtocolService
from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREventType,
    EHREvent,
)
from healthchain.interop import InteropEngine


class SOAPEvent(EHREvent):
    """Special event type for SOAP messages"""

    raw_xml: str = Field(default="")


class SOAPEventPublisher(ProtocolService):
    """Service for handling SOAP-based CDA documents"""

    def __init__(
        self,
        system_type: str = "EHR_CDA",
        dispatcher: EventDispatcher = None,
        soap_wsdl: str = None,
        **options,
    ):
        super().__init__(**options)
        self.system_type = system_type
        self.dispatcher = dispatcher or EventDispatcher()
        self.soap_wsdl = soap_wsdl
        self.interop_engine = InteropEngine()

        # Register default handlers
        self.register_handler("cda_document", self.handle_cda_document)

    async def handle_cda_document(self, soap_message: Dict) -> Dict[str, Any]:
        """Handle incoming CDA document via SOAP"""
        # Extract CDA from SOAP message
        cda_xml = soap_message.get("ClinicalDocument", "")

        # Transform to FHIR
        fhir_resources = self.interop_engine.to_fhir(cda_xml, "CDA")

        # Create event
        event = SOAPEvent(
            event_type=EHREventType.PATIENT_ADMISSION,
            source_system=self.system_type,
            timestamp=datetime.now(),
            payload=fhir_resources,
            metadata={"original_format": "CDA"},
            raw_xml=cda_xml,
        )

        # Dispatch event
        results = await self.dispatcher.dispatch_event(event)

        return {
            "status": "success",
            "event_id": str(event.timestamp),
            "resources_created": len(fhir_resources),
            "handlers_executed": len(results),
        }

    def soap_handler(self, event_type: EHREventType):
        """
        Decorator to register SOAP event handlers

        Args:
            event_type: The type of event to handle

        Returns:
            Decorator function
        """

        def decorator(handler):
            self.dispatcher.register_handler(event_type, handler)
            return handler

        return decorator
