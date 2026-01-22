# Create Gateway

Expose your pipeline as a CDS Hooks service that EHRs can call.

## What is CDS Hooks?

**CDS Hooks** is a standard for integrating clinical decision support with EHR systems. When a clinician performs an action (like opening a patient chart), the EHR calls your CDS service, and you return helpful information as "cards."

The flow:

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Clinician  │────────>│    EHR      │────────>│  Your CDS   │
│  opens      │         │  (Epic,     │  HTTP   │  Service    │
│  chart      │         │   Cerner)   │  POST   │             │
└─────────────┘         └─────────────┘         └─────────────┘
                               │                       │
                               │<──────────────────────│
                               │    CDS Cards          │
                               ▼
                        ┌─────────────┐
                        │  Display    │
                        │  alerts to  │
                        │  clinician  │
                        └─────────────┘
```

## Create the CDS Service

Create a file called `app.py`:

```python
from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.io import Document
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse, Card
from pipeline import create_clinical_pipeline

# Initialize the HealthChain API
app = HealthChainAPI(title="ClinicalFlow CDS Service")

# Create your pipeline
nlp = create_clinical_pipeline()

# Create a CDS Hooks service
cds_service = CDSHooksService()

# Register a hook handler using the decorator
@cds_service.hook(
    "patient-view",  # Hook type: triggers when a clinician views a patient
    id="patient-alerts",
    title="Clinical Alert Service",
    description="Analyzes patient data and returns relevant clinical alerts",
)
def patient_alerts(request: CDSRequest) -> CDSResponse:
    """
    Process patient context and return CDS cards.

    Args:
        request: CDSRequest containing context and prefetch data
    """
    cards = []

    # Get patient conditions from prefetch (if available)
    prefetch = request.prefetch or {}
    conditions = prefetch.get("conditions", [])

    # If we have clinical notes, process them
    if clinical_note := prefetch.get("note"):
        doc = Document(clinical_note)
        result = nlp(doc)

        # Create cards for each extracted condition
        for entity in result.entities:
            cards.append(Card(
                summary=f"Condition detected: {entity['display']}",
                detail=f"SNOMED code: {entity['code']}",
                indicator="info",
                source={"label": "ClinicalFlow", "url": "https://healthchain.dev"}
            ))

    # Check for drug interaction alerts
    if len(conditions) > 2:
        cards.append(Card(
            summary="Multiple active conditions",
            detail=f"Patient has {len(conditions)} active conditions. Review for potential interactions.",
            indicator="warning",
            source={"label": "ClinicalFlow"}
        ))

    return CDSResponse(cards=cards)


# Register the CDS service with the app
app.include_router(cds_service)

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Understanding the Code

### The `@cds_service.hook` Decorator

This decorator registers your function as a CDS Hooks handler:

- **First argument**: The hook type (e.g., `patient-view`, `order-select`)
- **`id`**: Unique identifier for this service endpoint
- **`title`**: Human-readable name
- **`description`**: What the service does

### CDS Cards

Cards are the responses you return to the EHR. Each card has:

| Field | Description |
|-------|-------------|
| `summary` | Brief message shown to clinician |
| `detail` | Additional information (optional) |
| `indicator` | Urgency: `info`, `warning`, or `critical` |
| `source` | Attribution for the recommendation |

## Run the Service

Start your CDS service:

```bash
python app.py
```

Your service is now running at `http://localhost:8000`.

## Test the Endpoints

### Discovery Endpoint

CDS Hooks services must provide a discovery endpoint. Test it:

```bash
curl http://localhost:8000/cds/cds-discovery
```

Response:

```json
{
  "services": [
    {
      "id": "patient-alerts",
      "title": "Clinical Alert Service",
      "description": "Analyzes patient data and returns relevant clinical alerts",
      "hook": "patient-view"
    }
  ]
}
```

### Service Endpoint

Test calling your service:

```bash
curl -X POST http://localhost:8000/cds/cds-services/patient-alerts \
  -H "Content-Type: application/json" \
  -d '{
    "hookInstance": "test-123",
    "hook": "patient-view",
    "context": {
      "patientId": "patient-001",
      "userId": "doctor-001"
    },
    "prefetch": {
      "note": "Patient presents with chest pain and hypertension."
    }
  }'
```

## Interactive API Docs

HealthChain generates OpenAPI documentation. Visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## What's Next

Your CDS service is running! Now let's [test it properly](testing.md) with realistic patient data using HealthChain's sandbox.
