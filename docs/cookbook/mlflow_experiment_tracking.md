# Track Clinical NLP Experiments with MLflow

Monitor and compare healthcare AI model performance across experiments with HealthChain's native MLflow integration. You'll track a clinical NER pipeline, log healthcare-specific metadata, generate FHIR Provenance for audit trails, and compare model versions in the MLflow UI.

Check out the full working example [here](https://github.com/dotimplement/HealthChain/tree/main/cookbook/mlflow_clinical_nlp.py).

![](../assets/images/mlflow-experiment-tracking.png)

## Why Track Healthcare ML Experiments?

Healthcare AI requires more than standard ML metrics. You need to track:

- **Patient cohort metadata** - What population was the model trained/evaluated on?
- **Regulatory compliance** - HIPAA, FDA clearance status, audit requirements
- **Data provenance** - Which EHR sources contributed to training data?
- **Model lineage** - How does this version compare to production?

HealthChain's MLflow integration handles all of this while generating FHIR Provenance resources for interoperability with clinical systems.

## Setup

### Install Dependencies

```bash
pip install healthchain[mlflow] scispacy
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
```

### Verify MLflow Installation

```python
from healthchain.mlflow import is_mlflow_available

if is_mlflow_available():
    print("MLflow ready!")
else:
    print("Install mlflow: pip install mlflow")
```

## Quick Start: Track a Single Run

The simplest way to add tracking is with the `@track_model` decorator:

```python
from healthchain.mlflow import track_model
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP
from healthchain.io import Document

# Build NLP pipeline
pipeline = Pipeline[Document]()
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
nlp = pipeline.build()

@track_model(
    experiment="clinical-ner",
    tags={"model": "en_core_sci_sm", "task": "entity-extraction"},
)
def extract_conditions(text: str) -> list:
    """Extract medical conditions from clinical text."""
    doc = nlp(Document(text))
    entities = doc.nlp.get_entities()
    return [{"text": e["text"], "label": e["label"]} for e in entities]

# Each call creates a tracked MLflow run
result = extract_conditions("Patient presents with hypertension and diabetes.")
print(result)
# [{'text': 'hypertension', 'label': 'ENTITY'}, {'text': 'diabetes', 'label': 'ENTITY'}]
```

View results at `http://localhost:5000` after running `mlflow ui`.

## Full Example: Clinical NLP Experiment Tracking

Let's build a complete experiment tracking workflow with healthcare-specific context, custom metrics, and FHIR Provenance generation.

### Configure MLflow

```python
from healthchain.mlflow import MLFlowConfig, MLFlowTracker

config = MLFlowConfig(
    # Local tracking (or use remote server URL)
    tracking_uri="mlruns",

    # Experiment groups related runs
    experiment_name="clinical-ner-evaluation",

    # Default tags for all runs
    tags={
        "team": "nlp-research",
        "environment": "development",
    },
)

tracker = MLFlowTracker(config)
```

### Define Healthcare Context

Capture patient cohort and regulatory metadata for compliance:

```python
from healthchain.mlflow import HealthcareRunContext, PatientContext

# Describe the evaluation cohort (anonymized/aggregate only)
patient_context = PatientContext(
    cohort="General Medicine Inpatients",
    age_range="18-90",
    sample_size=500,
    inclusion_criteria=[
        "Admitted to general medicine ward",
        "Has discharge summary",
        "English-language notes",
    ],
    exclusion_criteria=[
        "Psychiatric admission",
        "Pediatric patients",
    ],
)

# Full healthcare context for the experiment
healthcare_context = HealthcareRunContext(
    model_id="clinical-ner-scispacy",
    version="1.0.0",
    patient_context=patient_context,
    organization="Research Hospital AI Lab",
    purpose="Extract diagnoses from discharge summaries",
    data_sources=["internal-ehr", "mimic-iv-notes"],
    regulatory_tags=["HIPAA", "IRB-approved"],
)
```

### Build the Tracked Pipeline

Add `MLFlowComponent` for automatic per-document metrics:

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP
from healthchain.io import Document
from healthchain.mlflow import MLFlowComponent

# Build pipeline with tracking
pipeline = Pipeline[Document]()
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
pipeline.add_node(
    MLFlowComponent(
        tracker,
        track_predictions=True,
        track_timing=True,
        prefix="ner",
    ),
    stage="tracking",
)
nlp = pipeline.build()
```

### Run the Experiment

```python
# Sample clinical notes for evaluation
clinical_notes = [
    "Patient is a 65-year-old male with history of hypertension and type 2 diabetes mellitus.",
    "Assessment: Community-acquired pneumonia. Plan: IV antibiotics and respiratory therapy.",
    "The patient has chronic kidney disease stage 3 and congestive heart failure.",
    "Diagnosis: Acute exacerbation of COPD. Started on bronchodilators and steroids.",
    "History of atrial fibrillation on anticoagulation. No active bleeding.",
]

# Run experiment with full tracking
with tracker.start_run(run_name="scispacy-v1.0.0-eval"):
    # Log healthcare context (includes FHIR Provenance)
    tracker.log_healthcare_context(healthcare_context)

    # Log model configuration
    tracker.log_params({
        "spacy_model": "en_core_sci_sm",
        "pipeline_version": "1.0.0",
        "batch_size": len(clinical_notes),
    })

    # Process documents
    all_entities = []
    for i, note in enumerate(clinical_notes):
        result = nlp(Document(note))
        entities = result.nlp.get_entities()
        all_entities.extend(entities)

        # Log per-document metrics
        tracker.log_metrics({
            "doc_entity_count": len(entities),
            "doc_text_length": len(note),
        }, step=i)

    # Log aggregate metrics
    tracker.log_metrics({
        "total_documents": len(clinical_notes),
        "total_entities": len(all_entities),
        "avg_entities_per_doc": len(all_entities) / len(clinical_notes),
    })

    # Log entity distribution as artifact
    entity_counts = {}
    for e in all_entities:
        label = e.get("label", "UNKNOWN")
        entity_counts[label] = entity_counts.get(label, 0) + 1

    tracker.log_dict(entity_counts, "entity_distribution.json")

    print(f"Processed {len(clinical_notes)} notes, extracted {len(all_entities)} entities")
```

### View Results in MLflow UI

Start the MLflow UI to explore your experiments:

```bash
mlflow ui --backend-store-uri mlruns
```

Navigate to `http://localhost:5000` to see:

- **Experiment overview** - All runs grouped by experiment name
- **Run details** - Parameters, metrics, and artifacts for each run
- **Healthcare context** - Patient cohort and regulatory metadata as logged parameters
- **FHIR Provenance** - Audit trail artifact in FHIR JSON format

??? example "Example FHIR Provenance Resource"

    The `healthcare_context.to_fhir_provenance()` method generates a FHIR R4 Provenance resource:

    ```json
    {
      "resourceType": "Provenance",
      "recorded": "2025-01-19T10:30:00Z",
      "activity": {
        "coding": [{
          "system": "http://terminology.hl7.org/CodeSystem/v3-DataOperation",
          "code": "DERIVE",
          "display": "derive"
        }]
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
          "display": "clinical-ner-scispacy:1.0.0"
        }
      }],
      "reason": [{
        "coding": [{
          "system": "https://healthchain.io/regulatory",
          "code": "HIPAA"
        }]
      }, {
        "coding": [{
          "system": "https://healthchain.io/regulatory",
          "code": "IRB-approved"
        }]
      }],
      "policy": [
        "internal-ehr",
        "mimic-iv-notes"
      ]
    }
    ```

## Comparing Model Versions

Track multiple model versions and compare performance:

```python
models_to_evaluate = [
    ("en_core_sci_sm", "1.0.0"),
    ("en_core_sci_md", "1.0.0"),
    ("en_core_sci_lg", "1.0.0"),
]

for model_name, version in models_to_evaluate:
    # Build pipeline for this model
    pipeline = Pipeline[Document]()
    pipeline.add_node(SpacyNLP.from_model_id(model_name))
    nlp = pipeline.build()

    # Update context for this model
    healthcare_context.model_id = f"clinical-ner-{model_name}"
    healthcare_context.version = version

    with tracker.start_run(run_name=f"{model_name}-eval"):
        tracker.log_healthcare_context(healthcare_context)
        tracker.log_params({"spacy_model": model_name})

        # Run evaluation
        total_entities = 0
        for note in clinical_notes:
            result = nlp(Document(note))
            total_entities += len(result.nlp.get_entities())

        tracker.log_metrics({
            "total_entities": total_entities,
            "avg_entities_per_doc": total_entities / len(clinical_notes),
        })
```

Use the MLflow UI to compare runs side-by-side and select the best model for deployment.

## Pipeline Lifecycle Tracking

For long-running batch jobs, use lifecycle components to manage runs automatically:

```python
from healthchain.mlflow.components import (
    MLFlowStartRunComponent,
    MLFlowEndRunComponent,
    MLFlowComponent,
)

# Build pipeline with automatic run management
pipeline = Pipeline[Document]()
pipeline.add_node(
    MLFlowStartRunComponent(tracker, run_name="batch-processing"),
    position="first",
)
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
pipeline.add_node(MLFlowComponent(tracker, prefix="ner"))
pipeline.add_node(MLFlowEndRunComponent(tracker), position="last")

nlp = pipeline.build()

# Each pipeline execution is a complete tracked run
for note in clinical_notes:
    result = nlp(Document(note))
```

## Using the TrackedPipeline Wrapper

For existing pipelines, wrap them without modifying the original code:

```python
from healthchain.mlflow.decorators import TrackedPipeline

# Existing pipeline (unchanged)
pipeline = Pipeline[Document]()
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
nlp = pipeline.build()

# Wrap with tracking
tracked_nlp = TrackedPipeline(
    pipeline=nlp,
    config=config,
    run_name_prefix="inference",
)

# Each call is tracked as a separate run
for note in clinical_notes:
    result = tracked_nlp(Document(note))
```

## Batch Processing with Decorators

Use `@track_pipeline` for batch processing functions:

```python
from healthchain.mlflow import track_pipeline

@track_pipeline(
    experiment="clinical-batch-processing",
    log_input_shape=True,
    log_output_shape=True,
)
def process_patient_notes(notes: list) -> list:
    """Process a batch of clinical notes."""
    results = []
    for note in notes:
        doc = nlp(Document(note))
        results.append({
            "text": note[:100],
            "entity_count": len(doc.nlp.get_entities()),
        })
    return results

# Automatically logs: input_count, output_count, execution time
batch_results = process_patient_notes(clinical_notes)
```

## Custom Metric Extractors

Define custom metrics to extract from pipeline outputs:

```python
def count_conditions(data):
    """Count FHIR conditions in the document."""
    if hasattr(data, 'fhir') and hasattr(data.fhir, 'problem_list'):
        return float(len(data.fhir.problem_list))
    return 0.0

def has_high_confidence_entities(data):
    """Check if any entities have high confidence."""
    entities = data.nlp.get_entities()
    high_conf = [e for e in entities if e.get("confidence", 0) > 0.9]
    return 1.0 if high_conf else 0.0

tracking_component = MLFlowComponent(
    tracker,
    metric_extractors={
        "condition_count": count_conditions,
        "has_high_confidence": has_high_confidence_entities,
    },
)
```

## What You've Built

A complete experiment tracking system for healthcare AI:

| Feature | What It Does |
|---------|--------------|
| **Experiment tracking** | Log parameters, metrics, and artifacts for each model run |
| **Healthcare context** | Capture patient cohort, regulatory tags, and data sources |
| **FHIR Provenance** | Generate audit trail resources for compliance |
| **Model comparison** | Compare versions side-by-side in MLflow UI |
| **Pipeline integration** | Track metrics automatically within HealthChain pipelines |

!!! info "Use Cases"

    - **Model Development**: Track experiments during NER model development, compare scispacy vs. transformer-based approaches
    - **Validation Studies**: Log healthcare context for IRB-approved validation studies with full audit trails
    - **A/B Testing**: Compare model versions in production with metrics logged to the same experiment
    - **Regulatory Compliance**: Generate FHIR Provenance for FDA 510(k) submissions or HIPAA audits

!!! tip "Next Steps"

    - **Remote tracking server**: Deploy MLflow to a shared server for team collaboration
    - **Model registry**: Use MLflow's model registry to manage model versions and deployments
    - **Alerting**: Set up alerts when metrics drop below thresholds
    - **Integration**: Combine with the [ML Model Deployment](./ml_model_deployment.md) cookbook to track production inference
