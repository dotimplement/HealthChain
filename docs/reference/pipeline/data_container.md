# Data Container

The `healthchain.io.containers` module provides FHIR-native containers for healthcare data processing. These containers handle the complexities of clinical data formats while providing a clean Python interface for NLP/ML pipelines.

## DataContainer 📦

`DataContainer` is a generic base class for storing data of any type.

```python
from healthchain.io.containers import DataContainer

# Create a DataContainer with string data
container = DataContainer("Some data")

# Convert to dictionary and JSON
data_dict = container.to_dict()
data_json = container.to_json()

# Create from dictionary or JSON
container_from_dict = DataContainer.from_dict(data_dict)
container_from_json = DataContainer.from_json(data_json)
```

## Document 📄

The `Document` class is HealthChain's core container for clinical text and structured healthcare data. It handles FHIR resources natively, automatically manages validation and conversion, and integrates seamlessly with NLP models and CDS workflows.

Use Document containers for clinical notes, discharge summaries, patient records, and any healthcare data that combines text with structured FHIR resources.

| Attribute | Access | Primary Purpose | Key Features | Common Use Cases |
|-----------|--------|----------------|--------------|------------------|
| [**FHIR Data**](#fhir-data-docfhir) | `doc.fhir` | Manage clinical data in FHIR format | • Resource bundles<br>• Clinical lists (problems, meds, allergies)<br>• Document references<br>• CDS prefetch | • Store patient records<br>• Track medical history<br>• Manage clinical documents |
| [**NLP**](#nlp-component-docnlp) | `doc.nlp` | Process and analyze text | • Tokenization<br>• Entity recognition<br>• Embeddings<br>• spaCy integration | • Extract medical terms<br>• Analyze clinical text<br>• Generate features |
| [**CDS**](#clinical-decision-support-doccds) | `doc.cds` | Clinical decision support | • Recommendation cards<br>• Suggested actions<br>• Clinical alerts | • Generate alerts<br>• Suggest interventions<br>• Guide clinical decisions |
| [**Model Outputs**](#model-outputs-docmodels) | `doc.models` | Store ML model results | • Multi-framework support<br>• Task-specific outputs<br>• Text generation | • Store classifications<br>• Keep predictions<br>• Track generations |

### FHIR Data (`doc.fhir`)

The FHIR component provides production-ready management of FHIR resources with automatic validation, error handling, and convenient accessors for common clinical workflows:

**Storage and Management:**

   - Automatic `Bundle` creation and management
   - Resource type validation
   - Convenient access to common clinical data lists
   - Automatic extraction of `OperationOutcome` and `Provenance` resources into `doc.fhir.operation_outcomes` and `doc.fhir.provenances` (removed from bundle)

**Convenience Accessors:**

- `patient`: First Patient resource in the bundle, or `None`
- `patients`: List of Patient resources
- `problem_list`: List of `Condition` resources (diagnoses, problems)
- `medication_list`: List of `MedicationStatement` resources
- `allergy_list`: List of `AllergyIntolerance` resources

**Document Reference Management:**

   - Document relationship tracking (parent/child/sibling)
   - Attachment handling with `base64` encoding
   - Document family retrieval

**CDS Support:**

   - Support for CDS Hooks prefetch resources
   - Resource indexing by type

**Example: Clinical Documentation Workflow**

```python
from healthchain.io import Document
from healthchain.fhir import (
    create_condition,
    create_medication_statement,
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

# Document current medications
doc.fhir.medication_list = [
    create_medication_statement(
        subject="Patient/123",
        code="197361",
        display="Lisinopril 10 MG"
    ),
    create_medication_statement(
        subject="Patient/123",
        code="860975",
        display="Metformin 500 MG"
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

# Prepare data for CDS Hooks integration
prefetch = {
    "Condition": doc.fhir.problem_list,
    "MedicationStatement": doc.fhir.medication_list,
}
doc.fhir.prefetch_resources = prefetch

# CDS service can query prefetch data
conditions = doc.fhir.get_prefetch_resources("Condition")
print(f"Active conditions: {len(conditions)}")

# Handle errors and track data provenance
if doc.fhir.operation_outcomes:
    for outcome in doc.fhir.operation_outcomes:
        print(f"Warning: {outcome.issue[0].diagnostics}")

# Access patient demographics
if doc.fhir.patient:
    print(f"Patient: {doc.fhir.patient.name[0].given[0]} {doc.fhir.patient.name[0].family}")
```

**Technical Notes:**

- All FHIR resources are validated using [fhir.resources](https://github.com/nazrulworld/fhir.resources)
- Document relationships follow the FHIR [DocumentReference.relatesTo](https://www.hl7.org/fhir/documentreference-definitions.html#DocumentReference.relatesTo) standard

**Resource Documentation:**

- [FHIR Bundle](https://www.hl7.org/fhir/bundle.html)
- [FHIR DocumentReference](https://www.hl7.org/fhir/documentreference.html)
- [FHIR Condition](https://www.hl7.org/fhir/condition.html)
- [FHIR MedicationStatement](https://www.hl7.org/fhir/medicationstatement.html)
- [FHIR AllergyIntolerance](https://www.hl7.org/fhir/allergyintolerance.html)

### NLP Component (`doc.nlp`)

Process clinical text with medical NLP models and access extracted features:

- `get_tokens()`: Tokenized clinical text for downstream processing
- `get_entities()`: Medical entities with optional CUI codes (SNOMED CT, RxNorm)
- `get_embeddings()`: Vector representations for similarity search and clustering
- `get_spacy_doc()`: Direct access to spaCy document for custom processing
- `word_count()`: Token-based word count

**Example: Medical Entity Extraction**
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

Generate CDS Hooks cards and actions for real-time EHR integration:

- `cards`: Clinical recommendation cards displayed in EHR workflows
- `actions`: Suggested interventions (orders, referrals, documentation)

**Example: CDS Hooks Response**
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


### Model Outputs (`doc.models`)

Store and retrieve ML model predictions across multiple frameworks:

- `get_output(model_name, task)`: Retrieve model predictions by name and task
- `get_generated_text(model_name, task)`: Extract generated text from LLMs
- Supports Hugging Face, LangChain, spaCy, and custom models

**Example: Multi-Model Pipeline**
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

**Example: Complete Clinical Workflow**
```python
from healthchain.io import Document
from healthchain.fhir import create_condition
from healthchain.models import Card, Action

# Initialize with clinical note from EHR
doc = Document("67yo M presents with acute chest pain radiating to left arm, diaphoresis")

# Process with NLP model
print(f"Clinical note length: {doc.nlp.word_count()} words")
entities = doc.nlp.get_entities()

# Extract FHIR conditions from text
spacy_doc = doc.nlp.get_spacy_doc()
for ent in spacy_doc.ents:
    if ent.label_ == "CONDITION" and hasattr(ent._, "cui"):
        doc.fhir.problem_list.append(
            create_condition(
                subject="Patient/123",
                code=ent._.cui,
                display=ent.text
            )
        )

# Or use helper method for automatic extraction
doc.update_problem_list_from_nlp()

# Generate CDS alert based on findings
doc.cds.cards = [
    Card(
        summary="STEMI Alert - Activate Cath Lab",
        indicator="critical",
        detail="Patient meets criteria for ST-elevation myocardial infarction",
        source={"label": "Cardiology Protocol"},
    )
]

# Track model predictions
doc.models.add_output(
    model_name="cardiac_risk_model",
    task="classification",
    output={"risk_level": "high", "score": 0.89}
)

# Access all components
print(f"Problem list: {len(doc.fhir.problem_list)} conditions")
print(f"CDS cards: {len(doc.cds.cards)} alerts")
print(f"Risk assessment: {doc.models.get_output('cardiac_risk_model', 'classification')}")
```

[Document API Reference](../../api/containers.md#healthchain.io.containers.document)

## Tabular 📊

The `Tabular` class handles structured healthcare data like lab results, patient cohorts, and claims data. It wraps pandas DataFrame with healthcare-specific operations.

**Example: Patient Cohort Analysis**
```python
import pandas as pd
from healthchain.io.containers import Tabular

# Load patient cohort data
df = pd.DataFrame({
    'patient_id': ['P001', 'P002', 'P003'],
    'age': [45, 62, 58],
    'diagnosis': ['diabetes', 'hypertension', 'diabetes'],
    'hba1c': [7.2, None, 8.1]
})
cohort = Tabular(df)

# Analyze cohort characteristics
print(f"Cohort size: {cohort.row_count()} patients")
print(f"Average age: {cohort.data['age'].mean():.1f} years")
print(f"\nClinical measures:\n{cohort.describe()}")

# Filter for diabetic patients
diabetic_cohort = cohort.data[cohort.data['diagnosis'] == 'diabetes']
print(f"\nDiabetic patients: {len(diabetic_cohort)}")
print(f"Mean HbA1c: {diabetic_cohort['hba1c'].mean():.1f}%")

# Export for reporting
cohort.to_csv('patient_cohort_analysis.csv')
```

**Example: Lab Results Processing**
```python
# Load lab results from EHR export
labs = Tabular.from_csv('lab_results.csv')

print(f"Total lab orders: {labs.row_count()}")
print(f"Test types: {labs.data['test_name'].nunique()}")

# Identify abnormal results
abnormal = labs.data[labs.data['flag'] == 'ABNORMAL']
print(f"Abnormal results: {len(abnormal)} ({len(abnormal)/labs.row_count()*100:.1f}%)")
```

These containers provide a consistent, FHIR-aware interface for healthcare data processing throughout HealthChain pipelines, handling validation, conversion, and integration with clinical workflows automatically.
