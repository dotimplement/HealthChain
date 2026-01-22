# RFC 001: MLflow Integration for Healthcare Experiment Tracking

- Author: adamkells
- Status: Draft
- Created: 2026-01-22
- Related Issue(s): #185
- Related Discussion(s): N/A

## 1. Summary

Healthcare AI development requires experiment tracking that goes beyond standard ML metrics. Clinical deployments need audit trails, regulatory compliance documentation, patient cohort metadata, and data provenance records that integrate with healthcare information systems.

This RFC proposes adding MLflow integration to HealthChain through healthcare-specific context helpers and automatic FHIR Provenance generation. The design philosophy is to complement MLflow rather than wrap it, providing healthcare context that can be logged alongside standard ML metrics.

## 2. Problem statement

- **What problem are we trying to solve?**
  - ML researchers and engineers building healthcare AI need to track experiments with healthcare-specific metadata (patient cohorts, regulatory tags, data sources) that standard MLflow doesn't capture
  - Healthcare deployments require audit trails in interoperable formats (FHIR Provenance) for regulatory compliance
  - There's no standardized way to connect ML experiment tracking with healthcare data provenance requirements

- **Who is affected?**
  - ML researchers deploying models in clinical settings
  - Healthcare AI engineers who need audit trails for FDA/HIPAA compliance
  - Clinical informaticists who need to trace model outputs back to training data and cohorts

- **Why is this important now?**
  - MLflow integration is on the HealthChain roadmap
  - Growing regulatory scrutiny of healthcare AI requires better provenance documentation
  - Users are building clinical NLP pipelines with HealthChain and need experiment tracking

## 3. Goals and non-goals

### Goals

- Provide `HealthcareRunContext` and `PatientContext` Pydantic models for capturing healthcare-specific experiment metadata
- Implement `log_healthcare_context()` helper that logs healthcare metadata to an active MLflow run
- Automatically generate FHIR R4 Provenance resources for audit trails
- Support MLflow as an optional dependency (`pip install healthchain[mlflow]`)
- Provide clear documentation and cookbook examples

### Non-goals

- Wrapping or abstracting MLflow's core API (users call `mlflow.start_run()`, `mlflow.log_metrics()`, etc. directly)
- Automatic Pipeline-level tracking (future RFC scope)
- MLflow model registry integration for model deployment
- Support for other experiment tracking systems (W&B, Neptune, etc.)

## 4. Background and context

### Current State

HealthChain provides:
- `Pipeline[T]` for building NLP pipelines with healthcare data
- FHIR utilities for resource creation and validation
- No experiment tracking capabilities

### MLflow Overview

MLflow is the de facto standard for ML experiment tracking, providing:
- Run tracking with parameters, metrics, and artifacts
- Model registry for versioning and deployment
- UI for comparing experiments

### FHIR Provenance

FHIR R4 Provenance resources document the origin and history of healthcare data. They're used for:
- Audit trails required by HIPAA
- Documenting AI/ML model involvement in clinical decisions
- Tracing data lineage across systems

Relevant specifications:
- [FHIR R4 Provenance](https://www.hl7.org/fhir/provenance.html)
- [HL7 FHIR Provenance Participant Types](http://terminology.hl7.org/CodeSystem/provenance-participant-type)

## 5. Proposed design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User Code                                │
│  ┌─────────────────┐    ┌────────────────────────────────┐  │
│  │  mlflow.start_  │    │  log_healthcare_context(ctx)   │  │
│  │  run(), log_*   │    │                                │  │
│  └────────┬────────┘    └───────────────┬────────────────┘  │
│           │                             │                    │
└───────────┼─────────────────────────────┼────────────────────┘
            │                             │
            ▼                             ▼
┌───────────────────┐         ┌─────────────────────────────┐
│     MLflow        │◄────────│   healthchain.mlflow        │
│  (external pkg)   │         │  ├── HealthcareRunContext   │
│                   │         │  ├── PatientContext         │
│  - Runs           │         │  ├── log_healthcare_context │
│  - Params/Metrics │         │  └── to_fhir_provenance()   │
│  - Artifacts      │         └─────────────────────────────┘
└───────────────────┘
```

### Module Structure

```
healthchain/mlflow/
├── __init__.py      # Public API, optional import handling
└── context.py       # HealthcareRunContext, PatientContext models
```

### Data Models

#### PatientContext

Captures anonymized patient cohort information (no PHI):

```python
class PatientContext(BaseModel):
    cohort: str = "unspecified"           # e.g., "ICU patients"
    age_range: Optional[str] = None       # e.g., "18-65"
    sample_size: Optional[int] = None     # Number of patients
    inclusion_criteria: List[str] = []    # Inclusion criteria
    exclusion_criteria: List[str] = []    # Exclusion criteria
```

#### HealthcareRunContext

Main context model for healthcare experiment metadata:

```python
class HealthcareRunContext(BaseModel):
    model_id: str                              # Required: unique model identifier
    version: str                               # Required: version string
    patient_context: Optional[PatientContext]  # Anonymized cohort info
    organization: Optional[str]                # Responsible organization
    purpose: Optional[str]                     # Use case description
    data_sources: List[str] = []              # Data source identifiers
    regulatory_tags: List[str] = []           # e.g., ["HIPAA", "IRB-approved"]
    custom_metadata: Dict[str, Any] = {}      # Extension point
    recorded: Optional[datetime] = None        # Timestamp

    def to_fhir_provenance(self) -> Optional[Provenance]:
        """Generate FHIR R4 Provenance resource for audit trails."""
```

### API

#### log_healthcare_context()

```python
def log_healthcare_context(
    context: HealthcareRunContext,
    log_provenance: bool = True,
) -> Dict[str, Any]:
    """Log healthcare context to the active MLflow run.

    Args:
        context: HealthcareRunContext with healthcare metadata
        log_provenance: Whether to log FHIR Provenance as artifact

    Returns:
        Dictionary of logged parameters

    Raises:
        ImportError: If MLflow is not installed
        RuntimeError: If no MLflow run is active
    """
```

#### is_mlflow_available()

```python
def is_mlflow_available() -> bool:
    """Check if MLflow is installed and available."""
```

### MLflow Parameter Naming

Healthcare parameters use the `healthcare.` prefix for namespacing:

| Parameter | Description |
|-----------|-------------|
| `healthcare.model_id` | Model identifier |
| `healthcare.model_version` | Version string |
| `healthcare.organization` | Responsible organization |
| `healthcare.purpose` | Use case description |
| `healthcare.patient_cohort` | Cohort description |
| `healthcare.patient_age_range` | Age range |
| `healthcare.patient_sample_size` | Sample size |
| `healthcare.data_sources` | Comma-separated sources |
| `healthcare.regulatory_tags` | Comma-separated tags |

MLflow tags use the `healthchain.` prefix:

| Tag | Description |
|-----|-------------|
| `healthchain.model_id` | Model identifier |
| `healthchain.version` | Version string |
| `healthchain.has_provenance` | "true" if Provenance logged |

### FHIR Provenance Generation

The `to_fhir_provenance()` method generates a FHIR R4 Provenance resource:

- **target**: References the ML model output
- **recorded**: Timestamp of the run
- **activity**: DERIVE operation with purpose description
- **agent**: ML model as performer
- **policy**: URNs for data sources and regulatory tags

Example output:

```json
{
  "resourceType": "Provenance",
  "recorded": "2026-01-22T10:30:00Z",
  "target": [{"display": "Output of ML Model: clinical-ner v1.0.0"}],
  "activity": {
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/v3-DataOperation",
      "code": "DERIVE"
    }],
    "text": "Extract diagnoses from discharge summaries"
  },
  "agent": [{
    "type": {"coding": [{"code": "performer"}]},
    "who": {"display": "ML Model: clinical-ner v1.0.0"}
  }],
  "policy": [
    "urn:healthchain:datasource:internal-ehr",
    "urn:healthchain:regulatory:HIPAA"
  ]
}
```

### Usage Example

```python
import mlflow
from healthchain.mlflow import HealthcareRunContext, PatientContext, log_healthcare_context

context = HealthcareRunContext(
    model_id="clinical-ner",
    version="1.0.0",
    patient_context=PatientContext(
        cohort="General Medicine Inpatients",
        sample_size=500,
    ),
    regulatory_tags=["HIPAA", "IRB-approved"],
)

mlflow.set_experiment("clinical-nlp")

with mlflow.start_run(run_name="evaluation-v1"):
    # Log healthcare context (params + FHIR Provenance artifact)
    log_healthcare_context(context)

    # Standard MLflow usage
    mlflow.log_params({"spacy_model": "en_core_sci_sm"})
    mlflow.log_metrics({"f1_score": 0.87})
```

### Optional Dependency Handling

MLflow is an optional dependency:

```toml
# pyproject.toml
[project.optional-dependencies]
mlflow = ["mlflow>=2.0.0"]
```

The module handles missing MLflow gracefully:

```python
# healthchain/mlflow/__init__.py
try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False

# Context classes always available (no mlflow dependency)
from healthchain.mlflow.context import HealthcareRunContext, PatientContext
```

## 6. Alternatives considered

### Alternative 1: Full MLflow Wrapper

Wrap MLflow's entire API with healthcare-aware versions (`healthcare_start_run()`, `healthcare_log_metrics()`, etc.).

**Rejected because:**
- Adds maintenance burden tracking MLflow API changes
- Limits users who want MLflow features not exposed in wrapper
- Against HealthChain's philosophy of composability over abstraction

### Alternative 2: Pipeline-Level Automatic Tracking

Add `track_with_mlflow=True` parameter to Pipeline that automatically logs all runs.

**Deferred because:**
- Increases scope significantly
- Requires changes to Pipeline core
- Can be added in a follow-up RFC after this foundation is in place

### Alternative 3: Abstract Experiment Tracker Interface

Create an abstract interface supporting multiple backends (MLflow, W&B, Neptune).

**Rejected because:**
- Over-engineering for current needs
- MLflow is dominant in healthcare/research settings
- Can be revisited if demand emerges

## 7. Security, privacy, and compliance

### PHI Protection

- `PatientContext` is designed for **aggregate/anonymized** cohort data only
- No fields for individual patient identifiers
- Documentation explicitly warns against logging PHI
- Sample size and age ranges are aggregate statistics

### Audit Trail Support

- FHIR Provenance generation supports healthcare audit requirements
- Provenance resources can be exported to clinical systems
- Timestamps and model versions enable traceability

### Regulatory Alignment

- `regulatory_tags` field documents compliance status (HIPAA, FDA, IRB)
- Tags are logged as both MLflow parameters and FHIR Provenance policy URNs
- Does not enforce compliance; documents claimed status

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| User logs PHI in custom_metadata | Document warning; no technical prevention (user responsibility) |
| FHIR Provenance used incorrectly for legal compliance | Document that this is informational, not a compliance guarantee |

## 8. Migration and rollout plan

### Rollout Strategy

- **Phase 1 (this RFC)**: Ship as new optional module with documentation
- **Phase 2 (future)**: Gather feedback, consider Pipeline integration

### Installation

New optional dependency group:

```bash
pip install healthchain[mlflow]
```

### Backwards Compatibility

- No breaking changes to existing APIs
- New module only; existing code unaffected
- MLflow remains optional

### Rollback

- Remove `healthchain/mlflow/` directory
- Remove `mlflow` from optional dependencies
- No data migration needed (MLflow data is external)

## 9. Testing and observability

### Test Coverage

- Unit tests for `HealthcareRunContext` and `PatientContext` models
- Unit tests for `to_fhir_provenance()` output structure
- Integration tests for `log_healthcare_context()` with mocked MLflow
- Test `is_mlflow_available()` behavior with/without MLflow installed

### Test Strategy

```python
# Test context creation
def test_healthcare_run_context_required_fields():
    ctx = HealthcareRunContext(model_id="test", version="1.0")
    assert ctx.model_id == "test"

# Test FHIR Provenance generation
def test_to_fhir_provenance_structure():
    ctx = HealthcareRunContext(
        model_id="test",
        version="1.0",
        regulatory_tags=["HIPAA"],
    )
    provenance = ctx.to_fhir_provenance()
    assert provenance.resourceType == "Provenance"
    assert "urn:healthchain:regulatory:HIPAA" in provenance.policy

# Test MLflow integration (mocked)
def test_log_healthcare_context_logs_params(mock_mlflow):
    ctx = HealthcareRunContext(model_id="test", version="1.0")
    log_healthcare_context(ctx)
    mock_mlflow.log_params.assert_called()
```

### Observability

- Standard Python logging in module (`logging.getLogger(__name__)`)
- MLflow UI provides experiment visibility
- No new metrics/traces required for HealthChain itself

## 10. Open questions

1. **URN namespace**: Should `urn:healthchain:` URNs be registered or use a different scheme for FHIR Provenance policy references?

2. **Pipeline integration scope**: Should a follow-up RFC add `Pipeline.enable_tracking()` or keep tracking entirely external?

3. **Model registry**: Is there demand for MLflow Model Registry integration (model versioning, staging) in a future RFC?

4. **FHIR Provenance target**: Currently uses a display-only Reference. Should we support linking to actual FHIR resources when available?
