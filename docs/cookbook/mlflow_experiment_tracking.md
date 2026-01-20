# Track Clinical NLP Experiments with MLflow

Monitor and compare healthcare AI model performance using MLflow with HealthChain's healthcare-specific context and FHIR Provenance generation.

## Why Track Healthcare ML Experiments?

Healthcare AI requires more than standard ML metrics. You need to track:

- **Patient cohort metadata** - What population was the model trained/evaluated on?
- **Regulatory compliance** - HIPAA, FDA clearance status, audit requirements
- **Data provenance** - Which EHR sources contributed to training data?
- **Model lineage** - How does this version compare to production?

HealthChain provides `HealthcareRunContext` to capture this metadata and automatically generate FHIR Provenance resources for interoperability with clinical systems.

## Setup

```bash
pip install healthchain[mlflow]
```

Verify installation:

```python
from healthchain.mlflow import is_mlflow_available

if is_mlflow_available():
    print("MLflow ready!")
```

## Quick Start

Use MLflow directly with HealthChain's healthcare context helper:

```python
import mlflow
from healthchain.mlflow import HealthcareRunContext, log_healthcare_context
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP
from healthchain.io import Document

# Build your NLP pipeline
pipeline = Pipeline[Document]()
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
nlp = pipeline.build()

# Define healthcare context
context = HealthcareRunContext(
    model_id="clinical-ner-scispacy",
    version="1.0.0",
    organization="Hospital AI Lab",
    purpose="Extract diagnoses from discharge summaries",
    data_sources=["internal-ehr", "mimic-iv-notes"],
    regulatory_tags=["HIPAA", "IRB-approved"],
)

# Track with MLflow
mlflow.set_experiment("clinical-ner")

with mlflow.start_run(run_name="scispacy-evaluation"):
    # Log healthcare context (includes FHIR Provenance)
    log_healthcare_context(context)

    # Log model configuration
    mlflow.log_params({
        "spacy_model": "en_core_sci_sm",
        "pipeline_version": "1.0.0",
    })

    # Run your evaluation
    clinical_notes = [
        "Patient presents with hypertension and type 2 diabetes.",
        "Assessment: Community-acquired pneumonia.",
    ]

    total_entities = 0
    for note in clinical_notes:
        result = nlp(Document(note))
        entities = result.nlp.get_entities()
        total_entities += len(entities)

    # Log metrics
    mlflow.log_metrics({
        "total_documents": len(clinical_notes),
        "total_entities": total_entities,
        "avg_entities_per_doc": total_entities / len(clinical_notes),
    })
```

View results with `mlflow ui` at `http://localhost:5000`.

## Healthcare Context

### Patient Context

Capture anonymized patient cohort information:

```python
from healthchain.mlflow import HealthcareRunContext, PatientContext

patient_context = PatientContext(
    cohort="General Medicine Inpatients",
    age_range="18-90",
    sample_size=500,
    inclusion_criteria=[
        "Admitted to general medicine ward",
        "Has discharge summary",
    ],
    exclusion_criteria=[
        "Psychiatric admission",
        "Pediatric patients",
    ],
)

context = HealthcareRunContext(
    model_id="clinical-ner",
    version="1.0.0",
    patient_context=patient_context,
    regulatory_tags=["HIPAA"],
)
```

### FHIR Provenance

HealthChain automatically generates a FHIR R4 Provenance resource for audit trails:

```python
# Generate FHIR Provenance manually if needed
provenance = context.to_fhir_provenance()
print(provenance.model_dump_json(indent=2))
```

??? example "Example FHIR Provenance Resource"

    ```json
    {
      "resourceType": "Provenance",
      "recorded": "2025-01-19T10:30:00Z",
      "activity": {
        "coding": [{
          "system": "http://terminology.hl7.org/CodeSystem/v3-DataOperation",
          "code": "DERIVE",
          "display": "derive"
        }],
        "text": "Extract diagnoses from discharge summaries"
      },
      "agent": [{
        "type": {
          "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
            "code": "performer",
            "display": "Performer"
          }]
        },
        "who": {
          "display": "ML Model: clinical-ner-scispacy v1.0.0"
        }
      }],
      "reason": [{
        "text": "Regulatory compliance: HIPAA, IRB-approved"
      }],
      "policy": [
        "urn:healthchain:datasource:internal-ehr",
        "urn:healthchain:datasource:mimic-iv-notes"
      ]
    }
    ```

## Comparing Model Versions

Track multiple models in the same experiment:

```python
import mlflow
from healthchain.mlflow import HealthcareRunContext, log_healthcare_context
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP
from healthchain.io import Document

models_to_evaluate = [
    "en_core_sci_sm",
    "en_core_sci_md",
    "en_core_sci_lg",
]

clinical_notes = [
    "Patient is a 65-year-old male with hypertension and diabetes.",
    "Assessment: Community-acquired pneumonia.",
    "History of atrial fibrillation on anticoagulation.",
]

mlflow.set_experiment("clinical-ner-comparison")

for model_name in models_to_evaluate:
    # Build pipeline for this model
    pipeline = Pipeline[Document]()
    pipeline.add_node(SpacyNLP.from_model_id(model_name))
    nlp = pipeline.build()

    context = HealthcareRunContext(
        model_id=f"clinical-ner-{model_name}",
        version="1.0.0",
    )

    with mlflow.start_run(run_name=f"{model_name}-eval"):
        log_healthcare_context(context)
        mlflow.log_param("spacy_model", model_name)

        total_entities = 0
        for note in clinical_notes:
            result = nlp(Document(note))
            total_entities += len(result.nlp.get_entities())

        mlflow.log_metrics({
            "total_entities": total_entities,
            "avg_entities_per_doc": total_entities / len(clinical_notes),
        })
```

Use the MLflow UI to compare runs side-by-side.

## Batch Processing

For batch jobs, log step-wise metrics:

```python
import mlflow
from healthchain.mlflow import HealthcareRunContext, log_healthcare_context

mlflow.set_experiment("batch-processing")

with mlflow.start_run(run_name="batch-evaluation"):
    log_healthcare_context(HealthcareRunContext(
        model_id="clinical-ner",
        version="1.0.0",
    ))

    for i, note in enumerate(clinical_notes):
        result = nlp(Document(note))
        entities = result.nlp.get_entities()

        # Log per-document metrics with step
        mlflow.log_metrics({
            "doc_entity_count": len(entities),
            "doc_text_length": len(note),
        }, step=i)

    # Log final aggregate metrics
    mlflow.log_metrics({
        "total_documents": len(clinical_notes),
    })
```

## Remote Tracking Server

For team collaboration, use a remote MLflow server:

```python
import mlflow

# Set tracking URI before any operations
mlflow.set_tracking_uri("http://mlflow-server.example.com:5000")
mlflow.set_experiment("clinical-nlp")

with mlflow.start_run():
    # ... your tracking code
    pass
```

## API Reference

### `log_healthcare_context(context, log_provenance=True)`

Log healthcare context to the active MLflow run.

**Parameters:**

- `context` (HealthcareRunContext): Healthcare metadata to log
- `log_provenance` (bool): Whether to log FHIR Provenance artifact. Default: True

**Returns:** Dictionary of logged parameters

**Raises:**

- `ImportError`: If MLflow is not installed
- `RuntimeError`: If no MLflow run is active

### `HealthcareRunContext`

| Field | Type | Description |
|-------|------|-------------|
| `model_id` | str | Unique identifier for the model (required) |
| `version` | str | Model version string (required) |
| `patient_context` | PatientContext | Anonymized patient cohort information |
| `organization` | str | Organization responsible for the model |
| `purpose` | str | Purpose or use case for the model |
| `data_sources` | list[str] | Data sources used |
| `regulatory_tags` | list[str] | Regulatory compliance tags |
| `custom_metadata` | dict | Additional custom metadata |

### `PatientContext`

| Field | Type | Description |
|-------|------|-------------|
| `cohort` | str | Description of the patient cohort |
| `age_range` | str | Age range (e.g., "18-65") |
| `sample_size` | int | Number of patients |
| `inclusion_criteria` | list[str] | Inclusion criteria |
| `exclusion_criteria` | list[str] | Exclusion criteria |
