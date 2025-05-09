from fastapi import FastAPI, Depends, Security
from fastapi.security import OAuth2PasswordBearer
from typing import Dict

from ..core.manager import GatewayManager


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_app(gateway_config: Dict) -> FastAPI:
    """Create FastAPI application with gateway integration"""
    app = FastAPI(
        title="HealthChain Gateway API",
        description="Healthcare Integration Gateway",
        version="1.0.0",
    )

    # Initialize gateway manager as a dependency
    def get_gateway_manager():
        return GatewayManager(**gateway_config)

    # Define routes
    @app.get("/api/fhir/{resource_type}")
    async def route_fhir_request(
        resource_type: str,
        token: str = Security(oauth2_scheme),
        gateway: GatewayManager = Depends(get_gateway_manager),
    ):
        """Route FHIR API requests"""
        return await gateway.route_health_request("fhir", resource_type, {})

    @app.post("/api/ehr/webhook")
    async def handle_ehr_event(
        payload: Dict, gateway: GatewayManager = Depends(get_gateway_manager)
    ):
        """Handle incoming EHR events"""
        return await gateway.handle_ehr_webhook(payload)

    @app.post("/api/soap")
    async def handle_soap_message(
        soap_message: Dict, gateway: GatewayManager = Depends(get_gateway_manager)
    ):
        """Handle SOAP messages"""
        # Forward to appropriate handler
        pass

    return app
