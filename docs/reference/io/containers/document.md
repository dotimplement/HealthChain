# Document 📄

The `Document` class is a container for working with both clinical text and structured healthcare data. It natively manages FHIR resources, runs NLP over raw notes, tracks clinical document relationships, stores decision support outputs, and holds LLM model predictions.

Use Document containers for clinical notes, discharge summaries, patient records, and any healthcare data that combines text with structured FHIR resources.

## Usage

The main things you'll do with `Document`:

- Store and update clinical notes and FHIR Bundles
- Extract and manipulate diagnoses, meds, allergies, and documents
- Run NLP to extract entities or embeddings from text
- Generate & store CDS Hooks cards (recommendations, alerts)
- Attach model predictions for downstream use


## API Overview

**Document** has four key components (all accessible as attributes):

| Attribute | For |
|---|---|
| `doc.fhir` | FHIR management—Clinical lists, Bundles, DocReference, patient info |
| `doc.nlp`  | NLP features—entities, tokens, embeddings |
| `doc.cds`  | Decision support—recommendation cards, actions |
| `doc.models` | ML/LLM outputs—store/retrieve predictions, generations |


### FHIR Data (`doc.fhir`)

- Automatic FHIR Bundle creation and management
- Resource type validation
- Easy access to clinical data lists (e.g., problems, medications, allergies)
- OperationOutcome and Provenance resources automatically extracted and accessible as `doc.fhir.operation_outcomes` and `doc.fhir.provenances` (removed from main bundle)

**Convenience Accessors**

| Attribute         | Description                                              |
|-------------------|---------------------------------------------------------|
| `patient`         | First Patient resource in the bundle (or `None`)         |
| `patients`        | List of Patient resources                                |
| `problem_list`    | List of Condition resources (diagnoses, problems)        |
| `medication_list` | List of MedicationStatement resources                    |
| `allergy_list`    | List of AllergyIntolerance resources                     |

**Document Reference Management**

- Document relationship tracking (parent/child/sibling)
- Attachment handling with base64 encoding
- Document family retrieval

**CDS Support**

- Support for CDS Hooks prefetch resources
- Resource indexing by type


```python
from healthchain.io import Document
from healthchain.fhir import (
    create_condition,
    create_document_reference,
)

# Initialize with clinical text from EHR
doc = Document("Patient presents with uncontrolled hypertension and Type 2 diabetes")

# Build problem list with SNOMED CT codes
doc.fhir.problem_list = [
    create_condition(
        subject="Patient/123",
        code="38341003",
        display="Hypertension"
    ),
    create_condition(
        subject="Patient/123",
        code="44054006",
        display="Type 2 diabetes mellitus"
    )
]

# Track document versions and amendments
initial_note = create_document_reference(
    data="Initial assessment: Patient presents with chest pain",
    content_type="text/plain",
    description="Initial ED note"
)
initial_id = doc.fhir.add_document_reference(initial_note)

# Add amended note
amended_note = create_document_reference(
    data="Amended: Patient presents with chest pain, ruling out cardiac etiology",
    content_type="text/plain",
    description="Amended ED note"
)
amended_id = doc.fhir.add_document_reference(
    amended_note,
    parent_id=initial_id,
    relationship_type="replaces"
)

# Retrieve document history for audit trail
family = doc.fhir.get_document_reference_family(amended_id)
print(f"Original note: {family['parents'][0].description}")


# Handle errors and track data provenance
if doc.fhir.operation_outcomes:
    for outcome in doc.fhir.operation_outcomes:
        print(f"Warning: {outcome.issue[0].diagnostics}")

# Access patient demographics
if doc.fhir.patient:
    print(f"Patient: {doc.fhir.patient.name[0].given[0]} {doc.fhir.patient.name[0].family}")

# Prepare data for CDS Hooks integration
prefetch = {
    "Condition": doc.fhir.problem_list,
    "MedicationStatement": doc.fhir.medication_list,
}
doc.fhir.prefetch_resources = prefetch

# CDS service can query prefetch data
conditions = doc.fhir.get_prefetch_resources("Condition")
print(f"Active conditions: {len(conditions)}")
```

### NLP (`doc.nlp`)

- Medical text features: tokens, entities (`get_entities()`), embeddings (`get_embeddings()`)
- Direct spaCy doc access, fast word counting

```python
# Extract medical concepts from clinical note
doc = Document("Patient diagnosed with pneumonia, started on azithromycin")

# Get medical entities
entities = doc.nlp.get_entities()
for entity in entities:
    print(f"{entity.text}: {entity.label_}")  # "pneumonia: CONDITION"

# Access full spaCy document for custom processing
spacy_doc = doc.nlp.get_spacy_doc()
for ent in spacy_doc.ents:
    if hasattr(ent._, "cui"):
        print(f"{ent.text} -> SNOMED: {ent._.cui}")
```

### Clinical Decision Support (`doc.cds`)

- `cards`: Clinical recommendation cards displayed in EHR workflows
- `actions`: Suggested interventions (orders, referrals, documentation)

```python
from healthchain.models import Card, Action

# Generate clinical alert
doc.cds.cards = [
    Card(
        summary="Drug interaction detected",
        indicator="critical",
        detail="Warfarin + NSAIDs: Increased bleeding risk",
        source={"label": "Clinical Decision Support"},
    )
]

# Suggest action
doc.cds.actions = [
    Action(
        type="create",
        description="Order CBC to monitor platelets",
        resource={
            "resourceType": "ServiceRequest",
            "code": {"text": "Complete Blood Count"}
        }
    )
]
```


### LLM Model Outputs (`doc.models`)

- `get_output(model_name, task)`: Retrieve model predictions by name and task
- `get_generated_text(model_name, task)`: Extract generated text from LLMs
- Supports Hugging Face, LangChain, spaCy, and custom models

```python
# Store classification results
doc.models.add_output(
    model_name="clinical_classifier",
    task="diagnosis_prediction",
    output={"prediction": "diabetes", "confidence": 0.95}
)

# Store LLM summary
doc.models.add_output(
    model_name="gpt4",
    task="summarization",
    output="Patient presents with classic diabetic symptoms..."
)

# Retrieve outputs
diagnosis = doc.models.get_output("clinical_classifier", "diagnosis_prediction")
summary = doc.models.get_generated_text("gpt4", "summarization")
```

### Properties and Methods

```python
# FHIR access
print(doc.fhir.problem_list)
print(doc.fhir.patient)

# NLP
tokens = doc.nlp.get_tokens()
ents = doc.nlp.get_entities()

# Clinical decision support
cards = doc.cds.cards

# Model outputs
doc.models.add_output("my_model", "task", output={"foo": "bar"})
print(doc.models.get_output("my_model", "task"))
```

## Resource Docs

- [FHIR Bundle](https://www.hl7.org/fhir/bundle.html)
- [FHIR Condition](https://www.hl7.org/fhir/condition.html)
- [FHIR DocumentReference](https://www.hl7.org/fhir/documentreference.html)

## API Reference

See [Document API Reference](../../../api/containers.md#healthchain.io.containers.document) for full details.
