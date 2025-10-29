# Sandbox Client

The sandbox client provides a simplified interface for testing and validating your applications in realistic healthcare contexts. Use `SandboxClient` to quickly spin up demos and test with various data sources and workflows.

## Quick Example

Test CDS Hooks workflows with synthetic data:

```python
from healthchain.sandbox import SandboxClient

# Create client
client = SandboxClient(
    api_url="http://localhost:8000",
    endpoint="/cds/cds-services/my-service",
    workflow="encounter-discharge"
)

# Load data and send requests
client.load_from_registry("synthea", num_patients=5)
responses = client.send_requests()
```

## SandboxClient

### Initializing

```python
from healthchain.sandbox import SandboxClient

client = SandboxClient(
    api_url="http://localhost:8000",
    endpoint="/cds/cds-services/my-service",
    workflow="encounter-discharge",  # Optional, auto-detected if not provided
    protocol="rest",  # "rest" for CDS Hooks, "soap" for CDA
    timeout=10.0
)
```

### Loading Data

=== "From Registry"
    ```python
    # Load from pre-configured datasets
    client.load_from_registry("mimic-on-fhir", sample_size=10)
    client.load_from_registry("synthea", num_patients=5)

    # See available datasets
    from healthchain.sandbox import list_available_datasets
    print(list_available_datasets())
    ```

=== "From Files"
    ```python
    # Load single file
    client.load_from_path("./data/clinical_note.xml")

    # Load directory
    client.load_from_path("./data/cda_files/", pattern="*.xml")
    ```

=== "From Free Text CSV"
    ```python
    # Generate synthetic FHIR from clinical notes
    client.load_free_text(
        csv_path="./data/discharge_notes.csv",
        column_name="text",
        workflow="encounter-discharge",
        random_seed=42
    )
    ```

### Sending Requests

```python
# Send all queued requests
responses = client.send_requests()

# Save results
client.save_results("./output/")

# Get status
status = client.get_status()
print(status)
```

## Available Testing Scenarios

**CDS Hooks** (REST protocol):

- `workflow`: "patient-view", "encounter-discharge", "order-select", etc.
- Load FHIR Prefetch data
- Test clinical decision support services

**Clinical Documentation** (SOAP protocol):

- `workflow`: "sign-note-inpatient", "sign-note-outpatient"
- Load CDA XML documents
- Test SOAP/CDA document processing

## Complete Examples

=== "CDS Hooks Test"
    ```python
    from healthchain.sandbox import SandboxClient

    # Initialize for CDS Hooks
    client = SandboxClient(
        api_url="http://localhost:8000",
        endpoint="/cds/cds-services/discharge-summarizer",
        workflow="encounter-discharge",
        protocol="rest"
    )

    # Load and send
    client.load_from_registry("synthea", num_patients=3)
    responses = client.send_requests()
    client.save_results("./output/")
    ```

=== "Clinical Documentation Test"
    ```python
    from healthchain.sandbox import SandboxClient

    # Initialize for SOAP/CDA
    client = SandboxClient(
        api_url="http://localhost:8000",
        endpoint="/notereader/fhir/",
        workflow="sign-note-inpatient",
        protocol="soap"
    )

    # Load CDA files
    client.load_from_path("./data/cda_files/", pattern="*.xml")
    responses = client.send_requests()
    client.save_results("./output/")
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
    api_url="http://localhost:8000",
    endpoint="/cds/cds-services/my-service",
    workflow="patient-view"
)
client.load_from_registry("synthea", num_patients=5)
responses = client.send_requests()
```

## Next Steps

1. **Testing**: Use `SandboxClient` for local development and testing
2. **Production**: Migrate to [HealthChainAPI Gateway](../gateway/gateway.md)
3. **Protocols**: See [CDS Hooks](../gateway/cdshooks.md) and [SOAP/CDA](../gateway/soap_cda.md)
