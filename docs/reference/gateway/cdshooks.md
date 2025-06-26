# CDS Hooks Protocol

CDS Hooks is an [HL7](https://cds-hooks.hl7.org) published specification for clinical decision support that enables external services to provide real-time recommendations during clinical workflows.

## Overview

CDS hooks are triggered at specific events during a clinician's workflow in an electronic health record (EHR), such as when a patient record is opened or when an order is selected. The hooks communicate using [FHIR (Fast Healthcare Interoperability Resources)](https://hl7.org/fhir/).

CDS Hooks are unique in that they are *real-time* webhooks that are triggered by the EHR, not by external services. This makes them ideal for real-time clinical decision support and alerts, but also trickier to test and debug for a developer. They are also a relatively new standard, so not all EHRs support them yet.

| When      | Where | What you receive            | What you send back         | Common Use Cases |
| :-------- | :-----| :-------------------------- |----------------------------|-----------------|
| Triggered at certain events during a clinician's workflow | EHR  | The context of the event and FHIR resources that are requested by your service | "Cards" displaying text, actionable suggestions, or links to launch a [SMART](https://smarthealthit.org/) app | Allergy alerts, medication reconciliation, clinical decision support |

## HealthChainAPI Integration

Use the `CDSHooksService` with HealthChainAPI to handle CDS Hooks workflows:

```python
from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.models import CDSRequest, CDSResponse

app = HealthChainAPI()
cds = CDSHooksService()

@cds.hook("patient-view", id="allergy-alerts")
def check_allergies(request: CDSRequest) -> CDSResponse:
    # Your AI logic here
    return CDSResponse(cards=[...])

app.register_service(cds, path="/cds")
```

## Supported Workflows

| Workflow Name | Description | Trigger | Status |
|-----------|-------------|---------|----------|
| `patient-view` | Triggered when a patient chart is opened | Opening a patient's chart | ✅ |
| `order-select` | Triggered when a new order is selected | Selecting a new order | ⏳ |
| `order-sign` | Triggered when orders are being signed | Signing orders | ⏳ |
| `encounter-discharge` | Triggered when a patient is being discharged | Discharging a patient | ✅ |

## API Endpoints

When registered with HealthChainAPI, the following endpoints are automatically created:

| Endpoint | Method | Function | Description |
|------|--------|----------|-------------|
| `/cds-services` | GET | Service Discovery | Lists all available CDS services |
| `/cds-services/{id}` | POST | Hook Execution | Executes the specified CDS hook |

## Request/Response Format

### CDSRequest Example

```json
{
   "hookInstance": "23f1a303-991f-4118-86c5-11d99a39222e",
   "fhirServer": "https://fhir.example.org",
   "hook": "patient-view",
   "context": {
     "patientId": "1288992",
     "userId": "Practitioner/example"
    },
   "prefetch": {
      "patientToGreet": {
        "resourceType": "Patient",
        "gender": "male",
        "birthDate": "1925-12-23",
        "id": "1288992",
        "active": true
      }
   }
}
```

### CDSResponse Example

```json
{
  "cards": [{
    "summary": "Bilirubin: Based on the age of this patient consider overlaying bilirubin results",
    "indicator": "info",
    "detail": "The focus of this app is to reduce the incidence of severe hyperbilirubinemia...",
    "source": {
      "label": "Intermountain",
      "url": null
    },
    "links": [{
      "label": "Bilirubin SMART app",
      "url": "https://example.com/launch",
      "type": "smart"
    }]
  }]
}
```

## Supported FHIR Resources

- `Patient`
- `Encounter`
- `Procedure`
- `MedicationRequest`

For more information, see the [official CDS Hooks documentation](https://cds-hooks.org/).
