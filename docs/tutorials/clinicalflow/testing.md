# Test with Sandbox

Validate your CDS service with realistic patient data using HealthChain's sandbox.

## What is the Sandbox?

The **Sandbox** simulates what an EHR like Epic does - it sends CDS Hooks requests to your service with patient data. Instead of connecting to a real EHR (which requires authentication, network access, and real patients), the sandbox lets you:

- Load test data from files or generate synthetic patients
- Send CDS Hooks requests to your service (just like Epic would)
- Collect and analyze the responses

Think of it as a "fake EHR" for development and testing.

## Prepare Test Data

First, create sample data that matches what an EHR would send. This is the same CDS Hooks request format we saw in [FHIR Basics](fhir-basics.md#how-fhir-flows-into-cds-hooks).

Create a `data` directory:

```bash
mkdir data
```

Create `data/test_request.json` - this is a complete CDS Hooks request:

```json
{
  "hookInstance": "test-instance-001",
  "hook": "patient-view",
  "context": {
    "userId": "Practitioner/dr-smith",
    "patientId": "patient-001"
  },
  "prefetch": {
    "patient": {
      "resourceType": "Patient",
      "id": "patient-001",
      "name": [{"given": ["John"], "family": "Smith"}],
      "birthDate": "1970-01-15",
      "gender": "male"
    },
    "conditions": {
      "resourceType": "Bundle",
      "type": "searchset",
      "entry": [
        {
          "resource": {
            "resourceType": "Condition",
            "id": "condition-hypertension",
            "code": {
              "coding": [{
                "system": "http://snomed.info/sct",
                "code": "38341003",
                "display": "Hypertension"
              }]
            },
            "subject": {"reference": "Patient/patient-001"},
            "clinicalStatus": {"coding": [{"code": "active"}]}
          }
        },
        {
          "resource": {
            "resourceType": "Condition",
            "id": "condition-diabetes",
            "code": {
              "coding": [{
                "system": "http://snomed.info/sct",
                "code": "73211009",
                "display": "Diabetes mellitus"
              }]
            },
            "subject": {"reference": "Patient/patient-001"},
            "clinicalStatus": {"coding": [{"code": "active"}]}
          }
        }
      ]
    },
    "note": "Patient is a 65-year-old male presenting with chest pain and shortness of breath. History includes hypertension and diabetes, both well-controlled on current medications."
  }
}
```

This sample includes:

- **Patient demographics** - John Smith, born 1970
- **Two conditions** - Hypertension and Diabetes (matching what our pipeline recognizes)
- **Clinical note** - Free text that our NLP pipeline will process

## Quick Test with curl

The fastest way to test is with the sample data directly. With your service running, send the request:

```bash
curl -X POST http://localhost:8000/cds/cds-services/patient-alerts \
  -H "Content-Type: application/json" \
  -d @data/test_request.json
```

You should see a response with cards for the detected conditions.

## Create a Test Script

For more control, create `test_service.py`:

```python
import json
import requests

# Load the test request
with open("./data/test_request.json") as f:
    request_data = json.load(f)

# Send to your CDS service
response = requests.post(
    "http://localhost:8000/cds/cds-services/patient-alerts",
    json=request_data
)

# Analyze the response
result = response.json()
cards = result.get("cards", [])

print(f"Cards returned: {len(cards)}")
for card in cards:
    indicator = card.get("indicator", "info").upper()
    summary = card.get("summary")
    print(f"  [{indicator}] {summary}")
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

Expected output:

```
Cards returned: 4
  [INFO] Condition detected: Hypertension
  [INFO] Condition detected: Diabetes mellitus
  [INFO] Condition detected: Chest pain
  [INFO] Condition detected: Dyspnea
  [WARNING] Multiple active conditions
```

The pipeline extracted four conditions from the clinical note text - exactly what we built it to do.

## Advanced Usage
### Batch Testing with SandboxClient

For testing with multiple patients or larger datasets, use the `SandboxClient`:

```python
from healthchain.sandbox import SandboxClient

# Create a client pointing to your service
client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/patient-alerts",
    workflow="patient-view"
)

# Load FHIR bundles - SandboxClient converts them to CDS requests
client.load_from_path("./data/bundles/", pattern="*.json")

# Send all requests and collect responses
responses = client.send_requests()

# Analyze results
print(f"Tested {len(responses)} patients")
for i, response in enumerate(responses):
    cards = response.get("cards", [])
    print(f"  Patient {i + 1}: {len(cards)} cards")
```

### Save Test Results

Save results for reporting or debugging:

```python
# Save responses to files
client.save_results(
    directory="./output/",
    save_request=True,
    save_response=True
)
```

### Preview Requests Before Sending

Inspect what will be sent without actually calling the service:

```python
# Preview queued requests
previews = client.preview_requests(limit=5)
for preview in previews:
    print(f"Request {preview['index']}: {preview['hook']}")

# Get full request data
request_data = client.get_request_data(format="dict")
```

## What's Next

Your service is tested and working! Learn about [production deployment](next-steps.md) and extending your CDS service.
