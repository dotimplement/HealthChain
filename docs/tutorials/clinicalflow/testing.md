# Test with Sandbox

Validate your CDS service with realistic patient data using HealthChain's sandbox.

## What is the Sandbox?

The **Sandbox** provides tools for testing CDS services without connecting to a real EHR. It can:

- Load test data from files or registries
- Send CDS Hooks requests to your service
- Save results for analysis

## Create a Test Script

Create a file called `test_service.py`:

```python
from healthchain.sandbox import SandboxClient

# Create a sandbox client pointing to your service
client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/patient-alerts",
    workflow="patient-view"
)

# Load test data from a directory of FHIR bundles
client.load_from_path("./data/", pattern="*.json")

# Send requests and collect responses
responses = client.send_requests()

# Analyze results
print(f"Sent {len(responses)} requests")
for i, response in enumerate(responses):
    print(f"\nPatient {i + 1}:")
    cards = response.get("cards", [])
    print(f"  Cards returned: {len(cards)}")
    for card in cards:
        print(f"    - {card.get('indicator', 'info').upper()}: {card.get('summary')}")
```

## Prepare Test Data

Before running the test, create some sample FHIR data. Create a `data` directory with a test file:

```bash
mkdir -p data
```

Create `data/test_patient.json`:

```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "test-patient-1",
        "name": [{"given": ["John"], "family": "Smith"}],
        "gender": "male",
        "birthDate": "1970-01-15"
      }
    },
    {
      "resource": {
        "resourceType": "Condition",
        "id": "condition-1",
        "subject": {"reference": "Patient/test-patient-1"},
        "code": {
          "coding": [{
            "system": "http://snomed.info/sct",
            "code": "38341003",
            "display": "Hypertension"
          }]
        },
        "clinicalStatus": {
          "coding": [{"code": "active"}]
        }
      }
    }
  ]
}
```

## Run the Test

Make sure your service is running in one terminal:

=== "uv"

    ```bash
    uv run python app.py
    ```

=== "pip"

    ```bash
    python app.py
    ```

Then in another terminal, run the test:

=== "uv"

    ```bash
    uv run python test_service.py
    ```

=== "pip"

    ```bash
    python test_service.py
    ```

## Using Clinical Notes

If your pipeline processes clinical text (like the one we built), you can load free-text notes from a CSV file:

```python
from healthchain.sandbox import SandboxClient

client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/patient-alerts",
    workflow="patient-view"
)

# Load clinical notes from CSV
# The CSV should have a column containing the clinical text
client.load_free_text(
    csv_path="./data/clinical_notes.csv",
    column_name="note_text",
    generate_synthetic=True  # Generates synthetic FHIR resources
)

responses = client.send_requests()
```

## Using Dataset Registries

Load data from supported dataset registries like MIMIC-on-FHIR:

```python
from healthchain.sandbox import SandboxClient

client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/patient-alerts",
    workflow="patient-view"
)

# Load from a dataset registry
client.load_from_registry(
    "mimic-on-fhir",
    data_dir="./data/mimic-fhir",
    resource_types=["Patient", "Condition", "MedicationStatement"],
    sample_size=5
)

responses = client.send_requests()
```

## Save Test Results

Save results for reporting or debugging:

```python
# Save responses to files
client.save_results(
    directory="./output/",
    save_request=True,
    save_response=True
)
```

## Preview Requests Before Sending

Inspect what will be sent without actually calling the service:

```python
# Preview queued requests
previews = client.preview_requests(limit=5)
for preview in previews:
    print(f"Request {preview['index']}: {preview['hook']}")

# Get full request data
request_data = client.get_request_data(format="dict")
```

## Testing Different Hooks

Test different CDS Hooks workflows:

```python
# Test order-select hook
order_client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/drug-interactions",
    workflow="order-select"
)

# Test encounter-discharge hook
discharge_client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/discharge-summary",
    workflow="encounter-discharge"
)
```

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/patient-alerts",
    workflow="patient-view"
)
```

### Check Client Status

```python
status = client.get_status()
print(f"Requests queued: {status['requests_queued']}")
print(f"Responses received: {status['responses_received']}")
```

### Use Context Manager

The sandbox client supports context manager usage for automatic cleanup:

```python
with SandboxClient(
    url="http://localhost:8000/cds/cds-services/patient-alerts",
    workflow="patient-view"
) as client:
    client.load_from_path("./data/")
    responses = client.send_requests()
    # Results are auto-saved on exit if responses exist
```

## What's Next

Your service is tested and working! Learn about [production deployment](next-steps.md) and extending your CDS service.
