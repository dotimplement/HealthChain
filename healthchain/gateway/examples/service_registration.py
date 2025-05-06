"""
Example of using GatewayManager with service registration pattern.

This example demonstrates how to create various service providers and register them
with the GatewayManager, then use them to handle requests.
"""

from fastapi import FastAPI, Depends
from typing import Dict

from healthchain.gateway.core.manager import GatewayManager
from healthchain.gateway.clients.fhir import FHIRClient
from healthchain.gateway.protocols.cdshooks import CDSHooksService
from healthchain.gateway.protocols.soap import SOAPService

# Create FastAPI app
app = FastAPI(title="HealthChain Gateway API")

# Create gateway manager
gateway_manager = GatewayManager()

# Create services for different protocols
cds_hooks_service = CDSHooksService(
    service_id="note-guidance",
    description="Provides clinical guidance for clinical notes",
)

soap_service = SOAPService(
    service_name="ICDSServices", namespace="urn:epic-com:Common.2013.Services"
)

# Create FHIR client
fhir_client = FHIRClient(base_url="https://r4.smarthealthit.org")


# Register CDS Hooks handler with decorator
@cds_hooks_service.hook("patient-view")
async def handle_patient_view(context, prefetch):
    """Process patient-view CDS Hooks request"""
    # Implementation logic here
    return {
        "cards": [
            {
                "summary": "Example summary",
                "detail": "Example detailed guidance",
                "indicator": "info",
                "source": {
                    "label": "HealthChain Gateway",
                    "url": "https://healthchain.example.com",
                },
            }
        ]
    }


# Register Epic NoteReader handler with decorator
@soap_service.method("ProcessDocument")
def process_cda_document(session_id, work_type, organization_id, document):
    """Process CDA document from Epic"""
    # Implementation logic here
    return {"document": document, "error": None}


# Register FHIR operation handler with decorator
@fhir_client.operation("patient_search")
async def enhanced_patient_search(name=None, identifier=None, **params):
    """Enhanced patient search operation"""
    search_params = {}

    if name:
        search_params["name"] = name
    if identifier:
        search_params["identifier"] = identifier

    # Additional business logic here

    return fhir_client.client.server.request_json("Patient", params=search_params)


# Register services with gateway manager
gateway_manager.register_service("cdshooks", cds_hooks_service)
gateway_manager.register_service("soap", soap_service)
gateway_manager.register_service("fhir", fhir_client)


# Use dependency injection to provide gateway manager
def get_gateway_manager():
    return gateway_manager


# API endpoints
@app.get("/api/status")
async def get_status(manager: GatewayManager = Depends(get_gateway_manager)):
    """Get gateway status and available services"""
    services = manager.list_services()

    return {"status": "healthy", "services": services, "version": "1.0.0"}


@app.post("/api/cdshooks/{hook}")
async def cds_hooks_endpoint(
    hook: str,
    request_data: Dict,
    manager: GatewayManager = Depends(get_gateway_manager),
):
    """CDS Hooks endpoint"""
    cds_service = manager.get_service("cdshooks")
    return await cds_service.handle(hook, **request_data)


@app.post("/api/soap/{method}")
async def soap_endpoint(
    method: str,
    request_data: Dict,
    manager: GatewayManager = Depends(get_gateway_manager),
):
    """SOAP endpoint"""
    soap_service = manager.get_service("soap")
    return soap_service.handle(method, **request_data)


@app.get("/api/fhir/{resource_type}")
async def fhir_endpoint(
    resource_type: str,
    params: Dict,
    manager: GatewayManager = Depends(get_gateway_manager),
):
    """FHIR endpoint"""
    fhir_client = manager.get_service("fhir")
    return await fhir_client.handle(
        "search", resource_type=resource_type, params=params
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
