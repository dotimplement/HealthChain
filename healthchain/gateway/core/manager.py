from typing import Callable, Dict, Optional, List

from healthchain.gateway.protocols.fhir import FhirAPIGateway
from healthchain.gateway.events.ehr import EHREventGateway
from healthchain.gateway.security.proxy import SecurityProxy
from healthchain.gateway.events.dispatcher import EventDispatcher, EHREventType


class GatewayManager:
    """Main gateway orchestration layer"""

    def __init__(self, fhir_config: Dict, ehr_config: Optional[Dict] = None):
        self.security = SecurityProxy()
        self.fhir_gateway = FhirAPIGateway(**fhir_config)

        # Initialize event system if EHR config provided
        if ehr_config:
            self.event_dispatcher = EventDispatcher()
            self.ehr_gateway = EHREventGateway(
                system_type=ehr_config["system_type"], dispatcher=self.event_dispatcher
            )
        else:
            self.ehr_gateway = None
            self.event_dispatcher = None

    def get_available_routes(self) -> List[str]:
        """Get list of available routing destinations"""
        routes = ["fhir"]
        if self.ehr_gateway:
            routes.append("ehr")
        return routes

    def route_health_request(
        self, destination: str, request_type: str, params: Dict
    ) -> Dict:
        """
        Route health data requests to appropriate systems
        """
        self.security.log_route_access(destination, params.get("user_id"))

        if destination == "fhir":
            return self.fhir_gateway.route_request(request_type, params)
        elif destination == "ehr":
            if not self.ehr_gateway:
                raise ValueError("EHR gateway not configured")
            return self.ehr_gateway.route_request(request_type, params)
        else:
            raise ValueError(f"Unknown destination: {destination}")

    def register_event_handler(self, event_type: EHREventType, handler: Callable):
        """Register handler for specific EHR event type"""
        if not self.event_dispatcher:
            raise RuntimeError("Event system not initialized - no EHR config provided")

        self.event_dispatcher.register_handler(event_type, handler)

    async def handle_ehr_webhook(self, webhook_data: Dict):
        """Handle incoming webhook from EHR system"""
        if not self.ehr_gateway:
            raise RuntimeError("EHR gateway not configured")

        # Log and audit webhook receipt
        self.security.log_route_access(
            route="ehr_webhook", user_id=webhook_data.get("source", "unknown")
        )

        # Process webhook through EHR gateway
        await self.ehr_gateway.handle_incoming_event(webhook_data)
