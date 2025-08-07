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
    FHIRGateway, CDSHooksService, NoteReaderService
)

# Create the application
app = HealthChainAPI()

# Create gateways for different protocols
fhir = FHIRGateway()
fhir.add_source("main", "fhir://fhir.example.com/r4?client_id=...")
cds = CDSHooksService()
soap = NoteReaderService()

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
- `EventCapability`: A component that provides event dispatching
- `HealthChainAPI`: FastAPI wrapper for healthcare gateway registration
- Concrete gateway implementations:
  - `FHIRGateway`: Synchronous FHIR REST API protocol
  - `AsyncFHIRGateway`: Asynchronous FHIR REST API protocol
  - `CDSHooksService`: CDS Hooks protocol
  - `NoteReaderService`: SOAP/CDA protocol

## Quick Start

```python
from healthchain.gateway import HealthChainAPI, FHIRGateway
from fhir.resources.patient import Patient

# Create the app
app = HealthChainAPI()

# Create and register a FHIR gateway
fhir = FHIRGateway()
fhir.add_source("main", "fhir://fhir.example.com/r4?client_id=...")

@fhir.read(Patient)
async def read_patient(patient):
    # Custom logic for processing a patient
    return patient

app.register_gateway(fhir)

# Run with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
```

## Dependency Injection

The gateway module provides dependency injection for accessing registered gateways and services:

```python
from healthchain.gateway.api.dependencies import get_gateway_by_name
from fastapi import Depends

# Register gateways with explicit types
app.register_gateway(fhir)  # Implements FHIRGateway
app.register_gateway(cds)   # Implements CDSHooksService
app.register_gateway(soap)  # Implements NoteReaderService

# Get gateway dependencies in API routes
@app.get("/api/patient/{id}")
async def get_patient(
    id: str,
    fhir=Depends(get_gateway_by_name("fhir"))
):
    # Access to FHIR methods through dependency injection
    return await fhir.read("Patient", id)
```

This approach provides:
- Dependency injection for clean separation of concerns
- Easy access to registered gateways and services
- Runtime validation with detailed error messages
- Better testability through dependency override

## Context Managers

Context managers are available in the `AsyncFHIRGateway` and are a powerful tool for managing resource lifecycles in a safe and predictable way. They are particularly useful for:

- Standalone CRUD operations
- Creating new resources
- Bulk operations
- Cross-resource transactions
- When you need guaranteed cleanup/connection management

The decorator pattern is more for processing existing resources, while context managers are for managing resource lifecycles.

```python
@fhir.read(Patient)
async def read_patient_and_create_note(patient):
    # Use context manager to create related resources
    async with fhir.resource_context("DiagnosticReport") as report:
        report["subject"] = {"reference": f"Patient/{patient.id}"}
        report["status"] = "final"

    return patient
```
