# MLflow Integration for HealthChain

HealthChain provides native MLflow integration for experiment tracking in healthcare AI applications. This integration enables you to track model performance, log healthcare-specific metadata, and generate FHIR Provenance resources for audit trails.

## Installation

MLflow is an optional dependency. Install it with:

```bash
pip install healthchain[mlflow]
```

Or add it to your existing environment:

```bash
pip install mlflow
```

## Quick Start

```python
from healthchain.mlflow import MLFlowTracker, MLFlowConfig

# Configure tracking
config = MLFlowConfig(
    tracking_uri="mlruns",
    experiment_name="sepsis-prediction"
)
tracker = MLFlowTracker(config)

# Track a run
with tracker.start_run(run_name="v1.2.0"):
    tracker.log_params({"model_type": "xgboost", "threshold": 0.5})
    # ... run your model ...
    tracker.log_metrics({"accuracy": 0.92, "auc": 0.87})
```

## Core Components

### MLFlowConfig

Configuration for MLflow experiment tracking using Pydantic validation.

```python
from healthchain.mlflow import MLFlowConfig

config = MLFlowConfig(
    # URI for the MLFlow tracking server (local path or remote URL)
    tracking_uri="http://localhost:5000",

    # Name of the experiment (created if doesn't exist)
    experiment_name="clinical-nlp",

    # Optional custom artifact storage location
    artifact_location="/path/to/artifacts",

    # Default tags applied to all runs
    tags={"team": "ml-research", "project": "clinical-ai"},

    # Whether to log system metrics (requires psutil)
    log_system_metrics=False,

    # Whether to automatically log models
    log_models=True,

    # Optional separate URI for model registry
    registry_uri="http://localhost:5001",
)
```

### MLFlowTracker

The core class for experiment tracking operations.

```python
from healthchain.mlflow import MLFlowTracker, MLFlowConfig

config = MLFlowConfig(
    tracking_uri="mlruns",
    experiment_name="my-experiment"
)
tracker = MLFlowTracker(config)
```

#### Starting Runs

Use the context manager pattern to ensure runs are properly closed:

```python
with tracker.start_run(run_name="experiment-v1", tags={"version": "1.0"}) as run:
    # Your experiment code here
    pass
```

You can also nest runs:

```python
with tracker.start_run(run_name="parent-run"):
    with tracker.start_run(run_name="child-run", nested=True):
        # Nested experiment
        pass
```

#### Logging Parameters

Parameters are key-value pairs describing experiment configuration:

```python
with tracker.start_run(run_name="training"):
    tracker.log_params({
        "model_type": "random_forest",
        "n_estimators": 100,
        "max_depth": 10,
        "feature_list": ["age", "lab_values", "vitals"],  # Lists are JSON-serialized
    })
```

#### Logging Metrics

Metrics are numerical values measuring model performance:

```python
with tracker.start_run(run_name="evaluation"):
    # Log multiple metrics at once
    tracker.log_metrics({
        "accuracy": 0.92,
        "precision": 0.89,
        "recall": 0.94,
        "f1_score": 0.91,
    })

    # Log single metric
    tracker.log_metric("auc", 0.87)

    # Log time-series metrics with step
    for epoch in range(10):
        tracker.log_metrics({"loss": 1.0 / (epoch + 1)}, step=epoch)
```

#### Logging Artifacts

Artifacts are files associated with a run:

```python
with tracker.start_run(run_name="model-training"):
    # Log a single file
    tracker.log_artifact("model.pkl")

    # Log all files in a directory
    tracker.log_artifacts("./output/plots/")

    # Log a dictionary as JSON
    tracker.log_dict(
        {"config": {"learning_rate": 0.01}},
        "config.json"
    )

    # Log text content
    tracker.log_text("Model training notes...", "notes.txt")
```

#### Setting Tags

Tags provide additional metadata for filtering and organization:

```python
with tracker.start_run(run_name="production-run"):
    tracker.set_tags({
        "environment": "production",
        "model_version": "1.2.0",
        "deployment_target": "epic-integration",
    })

    # Or set individual tags
    tracker.set_tag("status", "validated")
```

#### Listing Experiments and Runs

```python
# List all experiments
experiments = tracker.list_experiments()
for exp in experiments:
    print(f"{exp['name']}: {exp['experiment_id']}")

# List runs for an experiment
runs = tracker.list_runs(experiment_name="my-experiment", max_results=50)
```

## Healthcare-Specific Context

### HealthcareRunContext

Captures healthcare metadata for ML experiment runs, including FHIR Provenance generation for audit trails.

```python
from healthchain.mlflow import HealthcareRunContext, PatientContext

# Define patient context (anonymized/aggregate data only)
patient_ctx = PatientContext(
    cohort="ICU patients",
    age_range="18-90",
    sample_size=1000,
    inclusion_criteria=["admitted to ICU", "age >= 18"],
    exclusion_criteria=["DNR orders", "transferred from other facility"],
)

# Create healthcare context
context = HealthcareRunContext(
    model_id="sepsis-predictor",
    version="1.2.0",
    patient_context=patient_ctx,
    organization="Hospital AI Lab",
    purpose="Early sepsis detection",
    data_sources=["MIMIC-IV", "internal-ehr"],
    regulatory_tags=["HIPAA", "FDA-cleared"],
)

# Log to MLflow
with tracker.start_run(run_name="clinical-validation"):
    tracker.log_healthcare_context(context)
```

### FHIR Provenance Generation

The healthcare context can generate FHIR R4 Provenance resources for regulatory compliance:

```python
context = HealthcareRunContext(
    model_id="clinical-nlp",
    version="2.0.0",
    purpose="Clinical note extraction",
    data_sources=["epic-fhir", "cerner-fhir"],
    regulatory_tags=["HIPAA"],
)

# Generate FHIR Provenance resource
provenance = context.to_fhir_provenance()

# Provenance is automatically logged when using log_healthcare_context()
# Or access it manually:
print(provenance.json(indent=2))
```

The generated Provenance resource includes:
- Model identification as the performing agent
- Activity type (DERIVE operation)
- Regulatory compliance tags as reasons
- Data sources as policy references
- Timestamp for audit trails

## Pipeline Integration

### MLFlowComponent

Add automatic tracking to HealthChain pipelines:

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP
from healthchain.io import Document
from healthchain.mlflow import MLFlowComponent, MLFlowTracker, MLFlowConfig

# Create tracker
config = MLFlowConfig(experiment_name="clinical-nlp")
tracker = MLFlowTracker(config)

# Build pipeline with tracking
pipeline = Pipeline[Document]()
pipeline.add_node(SpacyNLP.from_model_id("en_core_web_sm"))
pipeline.add_node(
    MLFlowComponent(
        tracker,
        track_predictions=True,
        track_timing=True,
        prefix="nlp",
    ),
    stage="tracking"
)
nlp = pipeline.build()

# Run with tracking
with tracker.start_run(run_name="batch-processing"):
    for doc in documents:
        result = nlp(Document(doc))  # Metrics logged automatically
```

#### Custom Metric Extractors

Define custom metrics to extract from data containers:

```python
def count_conditions(data):
    """Count FHIR conditions in the document."""
    if hasattr(data, 'fhir') and hasattr(data.fhir, 'problem_list'):
        return float(len(data.fhir.problem_list))
    return 0.0

tracking_component = MLFlowComponent(
    tracker,
    metric_extractors={
        "condition_count": count_conditions,
        "has_medications": lambda d: 1.0 if d.fhir.medication_list else 0.0,
    },
)
```

### Pipeline Lifecycle Components

For automatic run management within pipelines:

```python
from healthchain.mlflow.components import MLFlowStartRunComponent, MLFlowEndRunComponent

pipeline = Pipeline[Document]()
pipeline.add_node(
    MLFlowStartRunComponent(tracker, run_name="inference"),
    position="first"
)
pipeline.add_node(SpacyNLP.from_model_id("en_core_web_sm"))
pipeline.add_node(MLFlowComponent(tracker))
pipeline.add_node(MLFlowEndRunComponent(tracker), position="last")

# Run is automatically started and ended
result = pipeline(doc)
```

## Decorators

### @track_model

Track individual model inference calls:

```python
from healthchain.mlflow import track_model

@track_model(
    experiment="ner-models",
    tags={"model": "clinical-ner", "version": "1.0"},
    log_params={"threshold": 0.5},
)
def run_inference(text: str) -> dict:
    """Run NER on clinical text."""
    return model.predict(text)

# Each call creates a tracked run
result = run_inference("Patient has hypertension")
```

### @track_pipeline

Track pipeline execution:

```python
from healthchain.mlflow import track_pipeline

@track_pipeline(
    experiment="clinical-pipelines",
    log_input_shape=True,
    log_output_shape=True,
)
def process_documents(docs: list) -> list:
    """Process a batch of clinical documents."""
    return [pipeline(doc) for doc in docs]

# Automatically logs input count, output count, execution time
results = process_documents(documents)
```

### TrackedPipeline Wrapper

An alternative to decorators for wrapping existing pipelines:

```python
from healthchain.mlflow import MLFlowConfig
from healthchain.mlflow.decorators import TrackedPipeline

config = MLFlowConfig(experiment_name="clinical-nlp")
tracked = TrackedPipeline(
    pipeline=my_pipeline,
    config=config,
    run_name_prefix="batch-run",
)

# Each call is tracked as a separate run
for doc in documents:
    result = tracked(doc)
```

## Tracked Metrics

The MLFlowComponent automatically extracts and logs these metrics when available:

| Metric | Description |
|--------|-------------|
| `{prefix}.elapsed_seconds` | Time since first call in the run |
| `{prefix}.call_count` | Number of pipeline calls |
| `{prefix}.token_count` | Number of tokens (if NLP data present) |
| `{prefix}.entity_count` | Number of entities (if NLP data present) |
| `{prefix}.condition_count` | Number of FHIR Conditions |
| `{prefix}.hf_task_count` | Number of HuggingFace task results |
| `{prefix}.lc_task_count` | Number of LangChain task results |

## Checking MLflow Availability

Check if MLflow is installed at runtime:

```python
from healthchain.mlflow import is_mlflow_available

if is_mlflow_available():
    from healthchain.mlflow import MLFlowTracker
    # Use tracking
else:
    # Graceful fallback
    print("MLflow not installed, tracking disabled")
```

## Example: Complete Clinical NLP Workflow

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP
from healthchain.io import Document
from healthchain.mlflow import (
    MLFlowConfig,
    MLFlowTracker,
    MLFlowComponent,
    HealthcareRunContext,
    PatientContext,
)

# 1. Configure MLflow
config = MLFlowConfig(
    tracking_uri="http://mlflow-server:5000",
    experiment_name="clinical-ner-pipeline",
    tags={"team": "nlp", "environment": "staging"},
)
tracker = MLFlowTracker(config)

# 2. Define healthcare context
context = HealthcareRunContext(
    model_id="clinical-ner",
    version="2.1.0",
    patient_context=PatientContext(
        cohort="General inpatients",
        sample_size=500,
    ),
    purpose="Extract diagnoses from clinical notes",
    regulatory_tags=["HIPAA"],
)

# 3. Build pipeline with tracking
pipeline = Pipeline[Document]()
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_lg"))
pipeline.add_node(MLFlowComponent(tracker, prefix="ner"))
nlp = pipeline.build()

# 4. Run with full tracking
with tracker.start_run(run_name="batch-extraction-v2.1.0"):
    # Log healthcare context (includes FHIR Provenance)
    tracker.log_healthcare_context(context)

    # Log pipeline config
    tracker.log_params({
        "spacy_model": "en_core_sci_lg",
        "batch_size": 32,
    })

    # Process documents
    results = []
    for doc in clinical_notes:
        result = nlp(Document(doc))
        results.append(result)

    # Log final metrics
    tracker.log_metrics({
        "total_documents": len(results),
        "avg_entities_per_doc": sum(
            len(r.nlp.get_entities()) for r in results
        ) / len(results),
    })
```

## Best Practices

1. **Use meaningful experiment names** - Group related runs under descriptive experiment names (e.g., `sepsis-prediction-v2`, `clinical-ner-validation`)

2. **Tag runs for filtering** - Use tags to mark environment, model version, and purpose for easy filtering in the MLflow UI

3. **Log healthcare context** - Always use `HealthcareRunContext` for clinical AI to maintain audit trails and regulatory compliance

4. **Avoid logging PHI** - Use `PatientContext` for aggregate/anonymized cohort information only. Never log individual patient identifiers.

5. **Use context managers** - Always use `with tracker.start_run()` to ensure runs are properly closed, even on exceptions

6. **Log artifacts for reproducibility** - Log model configs, preprocessing scripts, and evaluation results as artifacts

7. **Track step-wise metrics** - For training loops, use the `step` parameter to track metrics over iterations
