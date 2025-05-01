from datetime import datetime
from typing import Dict

from healthchain.gateway.events.ehr import EHREventGateway
from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREventType,
    EHREvent,
)
from healthchain.interop import InteropEngine


class SOAPEvent(EHREvent):
    """Special event type for SOAP messages"""

    raw_xml: str


class SOAPEventGateway(EHREventGateway):
    """Gateway for handling SOAP-based CDA documents"""

    def __init__(self, system_type: str, dispatcher: EventDispatcher, soap_wsdl: str):
        super().__init__(system_type, dispatcher)
        # self.soap_client = Client(soap_wsdl)
        self.interop_engine = InteropEngine()

    async def handle_cda_document(self, soap_message: Dict):
        """Handle incoming CDA document via SOAP"""
        # Extract CDA from SOAP message
        cda_xml = soap_message["ClinicalDocument"]

        # Transform to FHIR
        fhir_resources = self.interop_engine.to_fhir(cda_xml, "CDA")

        # Create event
        event = SOAPEvent(
            event_type=EHREventType.PATIENT_ADMISSION,
            source_system="EHR_CDA",
            timestamp=datetime.now(),
            payload=fhir_resources,
            metadata={"original_format": "CDA"},
            raw_xml=cda_xml,
        )

        # Dispatch event
        await self.dispatcher.dispatch_event(event)
