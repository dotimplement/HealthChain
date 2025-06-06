# HealthChain Gateway Module

A secure gateway layer that manages routing, transformation, and event handling between healthcare systems with a focus on maintainable, compliant integration patterns.

## Architecture

The gateway module is built around a central `BaseGateway` abstraction that provides:

- A consistent interface for registering operation handlers
- Event dispatching for asynchronous notifications
- Route registration with FastAPI
- Request/response handling

All protocol implementations extend `BaseGateway` to provide protocol-specific functionality:

```python
from healthchain.gateway import (
    HealthChainAPI, BaseGateway,
    FHIRGateway, CDSHooksGateway, NoteReaderGateway
)

# Create the application
app = HealthChainAPI()

# Create gateways for different protocols
fhir = FHIRGateway(base_url="https://fhir.example.com/r4")
cds = CDSHooksGateway()
soap = NoteReaderGateway()

# Register protocol-specific handlers
@fhir.read(Patient)
def handle_patient_read(patient):
    return patient

@cds.hook("patient-view", id="allergy-check")
def handle_patient_view(request):
    return CDSResponse(cards=[...])

@soap.method("ProcessDocument")
def process_document(request):
    return CdaResponse(document=...)

# Register gateways with the application
app.register_gateway(fhir)
app.register_gateway(cds)
app.register_gateway(soap)
```

## Core Types

- `BaseGateway`: The central abstraction for all protocol gateway implementations
- `EventDispatcherMixin`: A reusable mixin that provides event dispatching
- `HealthChainAPI`: FastAPI wrapper for healthcare gateway registration
- Concrete gateway implementations:
  - `FHIRGateway`: FHIR REST API protocol
  - `CDSHooksGateway`: CDS Hooks protocol
  - `NoteReaderGateway`: SOAP/CDA protocol

## Quick Start

```python
from healthchain.gateway import create_app, FHIRGateway
from fhir.resources.patient import Patient

# Create the app
app = create_app()

# Create and register a FHIR gateway
fhir = FHIRGateway()

@fhir.read(Patient)
def read_patient(patient):
    # Custom logic for processing a patient
    return patient

app.register_gateway(fhir)

# Run with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
```

## Type Safety with Protocols

The gateway module uses Python's Protocol typing for robust interface definitions:

```python
# Register gateways with explicit types
app.register_gateway(fhir)  # Implements FHIRGatewayProtocol
app.register_gateway(cds)   # Implements CDSHooksGatewayProtocol
app.register_gateway(soap)  # Implements SOAPGatewayProtocol

# Get typed gateway dependencies in API routes
@app.get("/api/patient/{id}")
async def get_patient(
    id: str,
    fhir: FHIRGatewayProtocol = Depends(get_typed_gateway("FHIRGateway", FHIRGatewayProtocol))
):
    # Type-safe access to FHIR methods
    return await fhir.read("Patient", id)
```

This approach provides:
- Enhanced type checking and IDE auto-completion
- Clear interface definition for gateway implementations
- Runtime type safety with detailed error messages
- Better testability through protocol-based mocking
