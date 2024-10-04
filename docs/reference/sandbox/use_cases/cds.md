# Use Cases

## Clinical Decision Support (CDS)

CDS workflows are based on [CDS Hooks](https://cds-hooks.org/). CDS Hooks is an [HL7](https://cds-hooks.hl7.org) published specification for clinical decision support. For more information you can consult the [official documentation](https://cds-hooks.org/).

| When      | Where | What you receive            | What you send back         |
| :-------- | :-----| :-------------------------- |----------------------------|
| Triggered at certain events during a clinician's workflow, e.g. when a patient record is opened. | EHR  | The context of the event and FHIR resources that are requested by your service. e.g. patient ID, `Encounter` and `Patient`.  | “Cards” displaying text, actionable suggestions, or links to launch a [SMART](https://smarthealthit.org/) app from within the workflow.      |


CDS hooks communicate using [HL7 FHIR (Fast Healthcare Interoperability Resources)](https://hl7.org/fhir/). FHIR data are represented internally as `CdsFhirData` in HealthChain, so a CDS client must return a `CdsFhirData` object.

CDS service functions receive `CdsRequest` and return a list of `Card`. [Improved documentation coming soon]

[(Card API Reference | ](../../../api/use_cases.md#healthchain.models.responses.cdsresponse.Card)[CdsFhirData API Reference)](../../../api/data_models.md#healthchain.models.data.cdsfhirdata)

## Supported Workflows

| Workflow Name | Description | Trigger | Maturity |
|-----------|-------------|---------|----------|
| `patient-view` | Triggered when a patient chart is opened | Opening a patient's chart | ✅ |
| `order-select` | Triggered when a new order is selected | Selecting a new order | ⏳ |
| `order-sign` | Triggered when orders are being signed | Signing orders | ⏳ |
| `encounter-discharge` | Triggered when a patient is being discharged | Discharging a patient | ✅ |



## Generated API Endpoints

| Endpoint | Method | Function Name | API Protocol |
|------|--------|----------|--------------|
| `/cds-services` | GET | `cds_discovery` | REST |
| `/cds-services/{id}` | POST | `cds_service` | REST |

## What does the data look like?

### Example `CDSRequest`

```json
{
   "hookInstance" : "23f1a303-991f-4118-86c5-11d99a39222e",
   "fhirServer" : "https://fhir.example.org",
   "hook" : "patient-view",
   "context" : {
     "patientId" : "1288992",
     "userId" : "Practitioner/example"
    },
   "prefetch" : {
      "patientToGreet" : {
        "resourceType" : "Patient",
        "gender" : "male",
        "birthDate" : "1925-12-23",
        "id" : "1288992",
        "active" : true
      }
   }
}
```
### Example `CDSResponse`

```json
{
  "summary": "Bilirubin: Based on the age of this patient consider overlaying bilirubin [Mass/volume] results over a time-based risk chart",
  "indicator": "info",
  "detail": "The focus of this app is to reduce the incidence of severe hyperbilirubinemia and bilirubin encephalopathy while minimizing the risks of unintended harm such as maternal anxiety, decreased breastfeeding, and unnecessary costs or treatment.",
  "source": {
    "label": "Intermountain",
    "url": null
  },
  "links": [
    {
      "label": "Bilirubin SMART app",
      "url": "https://example.com/launch",
      "type": "smart"
   }
  ]
}

```

## Implemented FHIR Resources

- `Patient`
- `Encounter`
- `Procedure`
- `MedicationRequest`
