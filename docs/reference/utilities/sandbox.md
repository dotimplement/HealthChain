# Sandbox Client

The sandbox client provides a simplified interface for testing and validating your applications in realistic healthcare contexts. Use `SandboxClient` to quickly spin up demos and test with various data sources and workflows.

## Quick Example

Test CDS Hooks workflows with synthetic data:

```python
from healthchain.sandbox import SandboxClient

# Create client with full service URL and workflow
client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/my-service",
    workflow="encounter-discharge"
)

# Load data and send requests
client.load_from_registry(
    "synthea-patient",
    data_dir="./data/synthea",
    resource_types=["Condition", "MedicationStatement"],
    sample_size=5
    )
responses = client.send_requests()
```

## SandboxClient

### Initializing

```python
from healthchain.sandbox import SandboxClient

client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/my-service",
    workflow="encounter-discharge",  # Required
    protocol="rest",  # "rest" for CDS Hooks, "soap" for CDA
    timeout=10.0
)
```

### Workflow-Protocol Compatibility

The client validates workflow-protocol combinations at initialization:

| Protocol | Compatible Workflows |
|----------|---------------------|
| **REST** | `patient-view`, `encounter-discharge`, `order-select`, `order-sign` |
| **SOAP** | `sign-note-inpatient`, `sign-note-outpatient` |


### Loading Data

=== "From Registry"
    ```python
    # Load from pre-configured datasets
    client.load_from_registry(
        "mimic-on-fhir",
        data_dir="./data/mimic-fhir",
        resource_types=["MimicMedication"],
        sample_size=10
    )

    # Available datasets: "mimic-on-fhir", "synthea-patient"
    ```

=== "From Files"
    ```python
    # Load single file
    client.load_from_path("./data/clinical_note.xml")

    # Load directory with glob pattern
    client.load_from_path("./data/cda_files/", pattern="*.xml")
    ```

=== "From Free Text CSV"
    ```python
    # Generate synthetic FHIR from clinical notes
    client.load_free_text(
        csv_path="./data/discharge_notes.csv",
        column_name="text",
        generate_synthetic=True,  # Include synthetic FHIR resources
        random_seed=42
    )
    ```

See [Data Generator](data_generator.md) for more details on `.load_free_text()` `generate_synthetic` field.

## Dataset Registry

HealthChain provides two pre-configured dataset loaders for testing common FHIR test datasets with CDS Hooks workflows. Download the datasets and use `.load_from_registry()` to load from your local directory.

### Overview

| Dataset & Description                                                   | FHIR Version | Type               | File Format                 | Source                                                                            | Download Link                                            |
|------------------------------------------------------------------------|--------------|---------------------|-----------------------------|------------------------------------------------------------------------------------|---------------------------------------------------------|
| **MIMIC-on-FHIR**: MIMIC-IV on FHIR Demo Dataset                       | R4           | Real de-identified  | `.ndjson.gz` per resource type | [PhysioNet Project](https://physionet.org/content/mimic-iv-fhir-demo/2.1.0/)      | [Download ZIP](https://physionet.org/content/mimic-iv-fhir-demo/get-zip/2.1.0/)   |
| **Synthea**: Synthea FHIR Patient Records (100 Sample)                 | R4           | Synthetic           | `.json` Bundle per patient   | [Synthea Downloads](https://synthea.mitre.org/downloads)                          | [Download ZIP](https://arc.net/l/quote/hoquexhy)         |


### MIMIC-on-FHIR Loader

Real-world, de-identified FHIR R4 data from Beth Israel Deaconess Medical Center. Suitable for testing with real-world data distributions and clinical patterns

!!! tip "Full Dataset"
    The [MIMIC-on-FHIR demo dataset](https://physionet.org/content/mimic-iv-fhir-demo/2.1.0/) is open access and contains about 100 patients. Access to the [full dataset](https://physionet.org/content/mimic-iv-fhir/2.1/) requires PhysioNet credentialed access.

#### Directory Structure

```
data_dir/
└── fhir/
    ├── MimicMedication.ndjson.gz
    ├── MimicCondition.ndjson.gz
    ├── MimicObservation.ndjson.gz
    └── ... (other resource types)
```

#### Usage

=== "Basic"
    ```python
    client.load_from_registry(
        "mimic-on-fhir",
        data_dir="./data/mimic-iv-fhir",
        resource_types=["MimicMedication", "MimicCondition"]
    )
    ```

=== "With Sampling"
    ```python
    # Load random sample for faster testing
    client.load_from_registry(
        "mimic-on-fhir",
        data_dir="./data/mimic-iv-fhir",
        resource_types=["MimicMedication", "MimicObservation"],
        sample_size=5,  # 5 resources per type
        random_seed=42   # Reproducible sampling
    )
    ```

=== "Direct Loader for ML Workflows"
    ```python
    # Use loader directly for ML pipelines (faster, no validation)
    from healthchain.sandbox.loaders import MimicOnFHIRLoader
    from healthchain.io import Dataset

    loader = MimicOnFHIRLoader()

    # as_dict=True: Returns single bundle dict (fast, no FHIR validation)
    # Suitable for ML feature extraction workflows
    bundle = loader.load(
        data_dir="./data/mimic-iv-fhir",
        resource_types=["MimicObservationChartevents", "MimicPatient"],
        as_dict=True
    )

    # Convert to DataFrame for ML
    dataset = Dataset.from_fhir_bundle(
        bundle,
        schema="healthchain/configs/features/sepsis_vitals.yaml"
    )
    df = dataset.data

    # as_dict=False (default): Returns Dict[str, Bundle]
    # Validated Bundle objects grouped by resource type (for CDS Hooks)
    bundles = loader.load(
        data_dir="./data/mimic-iv-fhir",
        resource_types=["MimicMedication", "MimicCondition"]
    )
    # Use bundles["medicationstatement"] and bundles["condition"]
    ```

### Synthea Loader

Synthetic patient data generated by [Synthea](https://synthea.mitre.org), containing realistic FHIR Bundles (typically 100-500 resources per patient). Ideal for single-patient workflows that require diverse data scenarios.

!!! tip "Getting Synthea Data"
    Generate synthetic patients using [Synthea](https://github.com/synthetichealth/synthea) or [download sample data](https://synthea.mitre.org/downloads) from their releases. Each patient Bundle is self-contained with all clinical history.

#### Directory Structure

```
data_dir/
├── FirstName123_LastName456_uuid.json
├── FirstName789_LastName012_uuid.json
└── ... (one .json file per patient)
```

#### Usage

=== "First Patient (Quick Demo)"
    ```python
    # Automatically loads first .json file found
    client.load_from_registry(
        "synthea-patient",
        data_dir="./synthea_sample_data_fhir_latest"
        resource_type=["Condition"],  # Finds all Condition resources, loads all if not specified
    )
    ```

=== "By Patient ID"
    ```python
    client.load_from_registry(
        "synthea-patient",
        data_dir="./synthea_sample_data_fhir_latest",
        patient_id="a969c177-a995-7b89-7b6d-885214dfa253",
        resource_type=["Condition"],
    )
    ```

=== "With Resource Filtering"
    ```python
    # Load specific resource types with sampling
    client.load_from_registry(
        "synthea-patient",
        data_dir="./synthea_sample_data_fhir_latest",
        patient_id="a969c177-a995-7b89-7b6d-885214dfa253",
        resource_types=["Condition", "MedicationRequest", "Observation"],
        sample_size=5,  # 5 resources per type
        random_seed=42,
    )
    ```

### Request Inspection and Debugging

Before sending requests to your service, you can inspect and verify the queued data using several debugging methods. These are particularly useful for troubleshooting data loading issues or verifying request structure.

#### Preview Requests

Get a high-level summary of queued requests without retrieving full payloads:

```python
# Preview all queued requests
previews = client.preview_requests()

# Preview first 3 requests only
previews = client.preview_requests(limit=3)
print(previews)

# [{'index': 0, 'type': 'CdaRequest', 'protocol': 'SOAP', 'has_document': True}]
```

#### Get Request Data

Access the full request data in different formats for detailed inspection:

```python
# Access raw Pydantic models directly
for request in client.requests:
    print(f"Prefetch keys: {request.prefetch.keys()}")
    print(request.model_dump())

# Get as list of dictionaries (for serialization)
requests_dict = client.get_request_data(format="dict")
print(requests_dict[0].keys())  # See available fields

# Get as JSON string (for saving or logging)
requests_json = client.get_request_data(format="json")
with open("debug_requests.json", "w") as f:
    f.write(requests_json)
```

#### Check Client Status

Get the current state of your sandbox client:

```python
status = client.get_status()
print(status)

# {
#     "sandbox_id": "550e8400-e29b-41d4-a716-446655440000",
#     "url": "http://localhost:8000/cds/cds-services/my-service",
#     "protocol": "rest",
#     "workflow": "encounter-discharge",
#     "requests_queued": 5,
#     "responses_received": 0
# }
```

#### Clear and Reload

Reset the request queue to start fresh without creating a new client:

```python
# Clear all queued requests
client.clear_requests()

# Load new data
client.load_from_path("./different_data.json")

# Verify new queue
status = client.get_status()
print(f"New queue size: {status['requests_queued']}")
```

??? example "Example Debugging Workflow"
    ```python
    from healthchain.sandbox import SandboxClient

    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/discharge-summary",
        workflow="encounter-discharge"
    )

    # Load data
    client.load_free_text("data/notes.csv", column_name="text")

    # Debug before sending
    print("=== Client Status ===")
    print(client.get_status())

    print("\n=== Request Previews ===")
    for preview in client.preview_requests(limit=2):
        print(f"Request {preview['index']}: {preview['type']}")

    print("\n=== Inspecting First Request ===")
    first_request = client.requests[0]
    print(f"Hook: {first_request.hook}")
    print(f"Context: {first_request.context}")
    print(f"Prefetch keys: {first_request.prefetch.keys()}")
    print(f"Example DocumentReference: {first_request.prefetch['document'].model_dump()}")

    # If everything looks good, send
    responses = client.send_requests()
    ```


### Sending Requests

```python
# Send all queued requests
responses = client.send_requests()

# Save results to disk
client.save_results("./output/")

# Get client status
status = client.get_status()
print(status)
# {
#     "sandbox_id": "...",
#     "url": "http://localhost:8000/cds/...",
#     "protocol": "rest",
#     "workflow": "encounter-discharge",
#     "requests_queued": 5,
#     "responses_received": 5
# }
```

## Complete Examples

=== "CDS Hooks Test"
    ```python
    from healthchain.sandbox import SandboxClient

    # Initialize client for CDS Hooks workflow
    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/sepsis-alert",
        workflow="patient-view"
    )

    # Load MIMIC-on-FHIR data
    client.load_from_registry(
        "mimic-on-fhir",
        data_dir="./data/mimic-iv-fhir",
        resource_types=["MimicConditionED"],
        sample_size=5
    )

    # Optional: Inspect before sending
    # client.preview_requests()
    # client.get_status()

    # Send requests and save results
    responses = client.send_requests()
    client.save_results("./output/")
    ```

=== "Clinical Documentation Test"
    ```python
    from healthchain.sandbox import SandboxClient

    # Initialize client for SOAP/CDA workflow
    client = SandboxClient(
        url="http://localhost:8000/notereader/ProcessDocument/",
        workflow="sign-note-inpatient",
        protocol="soap"
    )

    # Load CDA documents from directory
    client.load_from_path("./data/cda_files/", pattern="*.xml")

    # Optional: Inspect before sending
    # client.preview_requests()

    # Send requests and save results
    responses = client.send_requests()
    client.save_results("./output/")
    ```

=== "Free Text CSV"
    ```python
    from healthchain.sandbox import SandboxClient

    # Initialize client for CDS workflow
    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/my-service",
        workflow="encounter-discharge"
    )

    # Load and generate FHIR from clinical notes
    client.load_free_text(
        csv_path="./data/discharge_notes.csv",
        column_name="text",
        generate_synthetic=True  # Adds synthetic data
    )

    # Optional: Inspect generated data
    # requests = client.get_request_data(format="dict")
    # print(requests[0]['prefetch'].keys())

    # Send requests
    responses = client.send_requests()
    ```

## Advanced Usage

`SandboxClient` supports method chaining and context manager patterns for more concise code.

### Method Chaining

All data loading methods return `self`, enabling fluent method chaining:

```python
from healthchain.sandbox import SandboxClient

# Chain initialization, loading, and sending
responses = (
    SandboxClient(
        url="http://localhost:8000/cds/cds-services/my-service",
        workflow="encounter-discharge"
    )
    .load_from_registry(
        "synthea-patient",
        data_dir="./data/synthea",
        sample_size=5
    )
    .send_requests()
)
```

### Context Manager

Use the context manager for automatic result saving on successful completion:

```python
# Auto-save results to ./output/ on successful exit
with SandboxClient(
    url="http://localhost:8000/cds/cds-services/my-service",
    workflow="encounter-discharge"
) as client:
    client.load_free_text(
        csv_path="./data/notes.csv",
        column_name="text"
    )
    responses = client.send_requests()
    # Results automatically saved on successful exit
```

## Migration Guide

!!! warning "Decorator Pattern Deprecated"
    The `@hc.sandbox` and `@hc.ehr` decorators with `ClinicalDecisionSupport` and `ClinicalDocumentation` base classes are deprecated. Use `SandboxClient` instead.

**Before:**

```python
@hc.sandbox
class TestCDS(ClinicalDecisionSupport):
    @hc.ehr(workflow="patient-view")
    def load_data(self):
        return prefetch_data
```

**After:**

```python
client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/my-service",
    workflow="patient-view"
)
client.load_from_registry(
    "synthea-patient",
    data_dir="./data/synthea",
    resource_types=["Condition", "Observation"],
    sample_size=10
)
responses = client.send_requests()
```
