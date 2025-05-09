from typing import Callable, Dict, Optional, List

from healthchain.gateway.clients.fhir import FHIRClient
from healthchain.gateway.security.proxy import SecurityProxy
from healthchain.gateway.events.dispatcher import EventDispatcher, EHREventType


class GatewayManager:
    """Main gateway orchestration layer"""

    def __init__(
        self, fhir_config: Optional[Dict] = None, ehr_config: Optional[Dict] = None
    ):
        self.security = SecurityProxy()
        self.event_dispatcher = EventDispatcher()
        self.services = {}

        # Initialize FHIR handler if config provided (legacy support)
        if fhir_config:
            self.fhir_service = FHIRClient(**fhir_config)
        else:
            self.fhir_service = None

    def register_service(self, service_id: str, service_provider):
        """
        Register a service provider with the gateway manager

        Args:
            service_id: Unique identifier for the service
            service_provider: Service provider instance implementing protocol or service interface
        """
        self.services[service_id] = service_provider
        return self

    def get_service(self, service_id: str):
        """Get a registered service by ID"""
        if service_id not in self.services:
            raise ValueError(f"Service '{service_id}' not registered")
        return self.services[service_id]

    def list_services(self) -> List[str]:
        """Get list of all registered service IDs"""
        return list(self.services.keys())

    def get_available_routes(self) -> List[str]:
        """Get list of available routing destinations"""
        routes = []
        if self.fhir_service:
            routes.append("fhir")
        if self.ehr_gateway:
            routes.append("ehr")
        # Add registered services as available routes
        routes.extend(self.list_services())
        return routes

    def route_health_request(
        self, destination: str, request_type: str, params: Dict
    ) -> Dict:
        """
        Route health data requests to appropriate systems
        """
        self.security.log_route_access(destination, params.get("user_id"))

        # Try routing to registered services first
        if destination in self.services:
            service = self.services[destination]
            return service.handle(request_type, **params)
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
