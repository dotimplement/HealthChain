"""
Example: Migrating from service module to gateway module

This example demonstrates how to migrate existing service module implementations
(CDS Hooks and Epic NoteReader) to the new gateway architecture.
"""

import logging


from healthchain.gateway import (
    create_app,
    CDSHooksHandler,
    SOAPEventPublisher,
    GatewayManager,
    SecurityProxy,
)
from healthchain.models.requests.cdarequest import CdaRequest

logger = logging.getLogger(__name__)

# 1. Create the FastAPI application with gateway components
app = create_app()

# 2. Configure security
security_proxy = SecurityProxy(secret_key="your-secure-key")

# 3. Set up CDS Hooks gateway
# This replaces the previous endpoint-based approach in service.py
cds_hooks = CDSHooksHandler(
    service_id="note-guidance",
    description="Provides clinical guidance for clinical notes",
    hook="patient-view",
)

# 4. Set up SOAP gateway for Epic NoteReader
# This replaces the previous SOAP implementation in soap/epiccdsservice.py
soap_gateway = SOAPEventPublisher(
    system_type="EHR_CDA",
    service_name="ICDSServices",
    namespace="urn:epic-com:Common.2013.Services",
)


# 5. Register the processor function for CDA documents
# This is where you would migrate your existing CDA processing logic
def process_cda_document(cda_request: CdaRequest):
    """
    Process a CDA document and return a response.
    Migrated from the existing epiccdsservice.py implementation.
    """
    try:
        # Your existing CDA processing logic here
        # ...

        # Return response in expected format
        return {
            "document": "<processed>CDA response document</processed>",
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error processing CDA document: {str(e)}")
        return {"document": "", "error": str(e)}


# Register the processor with the SOAP gateway
soap_gateway.register_processor(process_cda_document)

# 6. Mount the SOAP service to FastAPI
soap_gateway.mount_to_app(app, path="/soap/epiccds")

# 7. Create a gateway manager to orchestrate traffic
gateway_manager = GatewayManager()
gateway_manager.register_gateway("cdshooks", cds_hooks)
gateway_manager.register_gateway("soap", soap_gateway)


# 8. Define FastAPI endpoint for CDS Hooks
@app.post("/cds-services/{service_id}")
async def cds_hooks_endpoint(service_id: str, request_data: dict):
    if service_id == cds_hooks.service_id:
        # Process through the CDSHooksGateway
        return await cds_hooks.handle_request(request_data)
    else:
        return {"error": f"Unknown service ID: {service_id}"}


# 9. Define discovery endpoint for CDS Hooks services
@app.get("/cds-services")
async def discovery_endpoint():
    # Return CDS Hooks discovery response
    return {"services": [await cds_hooks.get_service_definition()]}


# To run the server:
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
