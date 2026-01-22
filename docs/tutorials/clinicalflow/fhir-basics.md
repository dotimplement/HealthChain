# FHIR Basics

Understand the healthcare data format you'll work with in HealthChain.

## What is FHIR?

**FHIR** (Fast Healthcare Interoperability Resources) is the modern standard for exchanging healthcare data. Think of it as "JSON for healthcare" - structured, standardized data that EHR systems like Epic and Cerner use.

## Key Resources for CDS

For our ClinicalFlow service, we'll work with three main FHIR resources:

### Patient

Identifies who the patient is:

```json
{
  "resourceType": "Patient",
  "id": "example-patient",
  "name": [{"given": ["John"], "family": "Smith"}],
  "birthDate": "1970-01-15",
  "gender": "male"
}
```

### Condition

Records diagnoses and health problems:

```json
{
  "resourceType": "Condition",
  "id": "example-condition",
  "code": {
    "coding": [{
      "system": "http://snomed.info/sct",
      "code": "38341003",
      "display": "Hypertension"
    }]
  },
  "subject": {"reference": "Patient/example-patient"},
  "clinicalStatus": {
    "coding": [{"code": "active"}]
  }
}
```

### MedicationStatement

Tracks what medications a patient is taking:

```json
{
  "resourceType": "MedicationStatement",
  "id": "example-med",
  "medicationCodeableConcept": {
    "coding": [{
      "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
      "code": "197361",
      "display": "Lisinopril 10 MG"
    }]
  },
  "subject": {"reference": "Patient/example-patient"},
  "status": "active"
}
```

## Working with FHIR in HealthChain

HealthChain provides utilities to work with FHIR resources easily:

```python
from healthchain.fhir import create_condition, create_patient
from fhir.resources.patient import Patient

# Create a patient with basic demographics
# Note: create_patient generates an auto-prefixed ID (e.g., "hc-abc123")
patient = create_patient(
    gender="male",
    birth_date="1970-01-15",
    identifier="MRN-12345"  # Optional patient identifier (e.g., MRN)
)

# Create a condition linked to the patient
# The 'subject' parameter is required and references the patient
condition = create_condition(
    subject=f"Patient/{patient.id}",  # Reference to the patient
    code="38341003",
    display="Hypertension",
    system="http://snomed.info/sct"
)

print(f"Created patient with ID: {patient.id}")
print(f"With condition: {condition.code.coding[0].display}")
```

## FHIR Bundles

When an EHR sends patient context, it often comes as a **Bundle** - a collection of related resources:

```python
from fhir.resources.bundle import Bundle

# A bundle might contain a patient, their conditions, and medications
bundle_data = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [
        {"resource": patient.model_dump()},
        {"resource": condition.model_dump()}
    ]
}

bundle = Bundle(**bundle_data)
print(f"Bundle contains {len(bundle.entry)} resources")
```

## The Document Container

HealthChain's `Document` container bridges clinical text and FHIR data:

```python
from healthchain.io import Document

# Create a document with clinical text
doc = Document(
    "Patient presents with chest pain and shortness of breath. "
    "History of hypertension and diabetes."
)

# The document can hold FHIR data extracted from text
print(f"Document text: {doc.text[:50]}...")

# After NLP processing, the document will contain:
# - Extracted entities
# - Generated FHIR resources
# - Problem lists, medications, etc.
```

## What's Next

Now that you understand FHIR basics, let's [build a pipeline](pipeline.md) that processes clinical text and extracts structured data.
