# FHIRProblemListExtractor

The `FHIRProblemListExtractor` is a pipeline component that automatically extracts NLP annotations and formats them into FHIR [Condition](https://www.hl7.org/fhir/condition.html) resources with the the category `problem-list-item` and the status `active`.

## Usage

### Basic Usage

```python
from healthchain.pipeline.components import FHIRProblemListExtractor

# Extract conditions with default settings
extractor = FHIRProblemListExtractor()
doc = extractor(doc)  # Extracts from NLP entities stored in document's .nlp.entities or spaCy doc
```

### Configuration Options

```python
# Use SNOMED CT codes
extractor = FHIRProblemListExtractor(
    patient_ref="Patient/456",  # optional, defaults to "Patient/123"
    code_attribute="snomed_id", # optional, defaults to "cui"
    coding_system="http://snomed.info/sct" # optional, defaults to "http://snomed.info/sct"
)

# Use ICD-10 codes
extractor = FHIRProblemListExtractor(
    patient_ref="Patient/456",
    code_attribute="icd10",
    coding_system="http://hl7.org/fhir/sid/icd-10"
)
```

## Entity Extraction

The component extracts entities from the document's NLP annotations.

### spaCy Entities

Extracts from spaCy entities with extension attributes:

```python
# spaCy entity with CUI code
ent._.cui = "C0015967"  # Extracted automatically
```

### Generic NLP Entities
Works with any NLP framework via generic entity dictionaries:
```python
entities = [
    {"text": "fever", "cui": "C0015967"},
    {"text": "hypertension", "snomed_id": "38341003"}
]
```

## FHIR Condition Creation

Example of a FHIR Condition resource created by the component:

```json
{
  "resourceType": "Condition",
  "id": "hc-0aa85ff7-5e40-472b-a676-cb3df83d8313",
  "clinicalStatus": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
        "code": "active",
        "display": "Active"
      }
    ]
  },
  "code": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "C0242429",  # extracted from doc entity
        "display": "sore throat"  # extracted from doc entity
      }
    ]
  },
  "subject": {
    "reference": "Patient/123"
  }
}
```


## MedicalCodingPipeline Integration

```python
from healthchain.pipeline import MedicalCodingPipeline

# Automatic problem extraction
pipeline = MedicalCodingPipeline(
    extract_problems=True,
    patient_ref="Patient/456",
    code_attribute="cui"
)
```

## Related Documentation

- [FHIR Condition Resources](https://www.hl7.org/fhir/condition.html)
- [Medical Coding Pipeline](../prebuilt_pipelines/medicalcoding.md)
- [Document Container](../../io/containers/document.md)
