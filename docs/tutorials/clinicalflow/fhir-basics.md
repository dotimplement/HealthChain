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

??? info "FHIR Versions in HealthChain"

    HealthChain uses **FHIR R5** as the default version. However, **STU3** and **R4B** are also supported for compatibility with different EHR systems.

    You can specify the version when working with FHIR resources, and HealthChain provides utilities for converting between versions when needed.

    For more details on version handling, see the [FHIR utilities reference](../../reference/utilities/fhir_helpers.md).

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

## How FHIR Flows into CDS Hooks

When an EHR like Epic calls your CDS service, it sends a **CDS Hooks request** containing patient data. The FHIR resources you just learned about arrive in the `prefetch` field:

```json
{
  "hookInstance": "abc-123-def-456",
  "hook": "patient-view",
  "context": {
    "userId": "Practitioner/dr-smith",
    "patientId": "patient-001"
  },
  "prefetch": {
    "patient": {
      "resourceType": "Patient",
      "id": "patient-001",
      "name": [{"given": ["John"], "family": "Smith"}],
      "birthDate": "1970-01-15",
      "gender": "male"
    },
    "conditions": {
      "resourceType": "Bundle",
      "type": "searchset",
      "entry": [
        {
          "resource": {
            "resourceType": "Condition",
            "id": "condition-hypertension",
            "code": {
              "coding": [{
                "system": "http://snomed.info/sct",
                "code": "38341003",
                "display": "Hypertension"
              }]
            },
            "subject": {"reference": "Patient/patient-001"},
            "clinicalStatus": {"coding": [{"code": "active"}]}
          }
        },
        {
          "resource": {
            "resourceType": "Condition",
            "id": "condition-diabetes",
            "code": {
              "coding": [{
                "system": "http://snomed.info/sct",
                "code": "73211009",
                "display": "Diabetes mellitus"
              }]
            },
            "subject": {"reference": "Patient/patient-001"},
            "clinicalStatus": {"coding": [{"code": "active"}]}
          }
        }
      ]
    },
    "note": "Patient is a 65-year-old male presenting with chest pain and shortness of breath. History includes hypertension and diabetes, both well-controlled on current medications."
  }
}
```

This is the complete picture:

1. **`context`** - Tells you who triggered the hook (the practitioner) and which patient
2. **`prefetch.patient`** - The Patient resource with demographics
3. **`prefetch.conditions`** - A Bundle of the patient's active conditions
4. **`prefetch.note`** - Clinical text your NLP pipeline will process

Your CDS service receives this request, processes the data, and returns clinical alert cards. We'll use this same sample data throughout the tutorial for testing.

## What's Next

Now that you understand FHIR basics and how data flows into CDS, let's [build a pipeline](pipeline.md) that processes clinical text and extracts structured data.
