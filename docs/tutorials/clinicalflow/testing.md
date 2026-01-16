# Test with Sandbox

Validate your CDS service with realistic patient data using HealthChain's sandbox.

## What is the Sandbox?

The **Sandbox** provides tools for testing CDS services without connecting to a real EHR. It can:

- Generate realistic patient data
- Send CDS Hooks requests to your service
- Validate responses against the specification
- Save results for analysis

## Create a Test Script

Create a file called `test_service.py`:

```python
from healthchain.sandbox import SandboxClient

# Create a sandbox client pointing to your service
client = SandboxClient(
    url="http://localhost:8000/cds-services/patient-alerts",
    workflow="patient-view"
)

# Generate synthetic test data
client.generate_data(
    num_patients=3,
    conditions_per_patient=2
)

# Send requests and collect responses
responses = client.send_requests()

# Analyze results
print(f"Sent {len(responses)} requests")
for i, response in enumerate(responses):
    print(f"\nPatient {i + 1}:")
    print(f"  Status: {response.status_code}")
    if response.ok:
        cards = response.json().get("cards", [])
        print(f"  Cards returned: {len(cards)}")
        for card in cards:
            print(f"    - {card.get('indicator', 'info').upper()}: {card.get('summary')}")
```

## Run the Test

Make sure your service is running, then:

```bash
python test_service.py
```

Expected output:

```
Sent 3 requests

Patient 1:
  Status: 200
  Cards returned: 2
    - INFO: Condition detected: Hypertension
    - WARNING: Multiple active conditions

Patient 2:
  Status: 200
  Cards returned: 1
    - INFO: Condition detected: Diabetes mellitus

Patient 3:
  Status: 200
  Cards returned: 3
    - INFO: Condition detected: Chest pain
    - INFO: Condition detected: Hypertension
    - WARNING: Multiple active conditions
```

## Using Real Test Datasets

Load data from Synthea (a synthetic patient generator):

```python
from healthchain.sandbox import SandboxClient

client = SandboxClient(
    url="http://localhost:8000/cds-services/patient-alerts",
    workflow="patient-view"
)

# Load from Synthea data directory
client.load_from_registry(
    "synthea-patient",
    data_dir="./data/synthea",
    resource_types=["Patient", "Condition", "MedicationStatement"],
    sample_size=5
)

responses = client.send_requests()
```

## Save Test Results

Save results for reporting or debugging:

```python
# Save responses to files
client.save_results("./output/test_results/")

# Results are saved as JSON:
# - output/test_results/request_1.json
# - output/test_results/response_1.json
# - output/test_results/summary.json
```

## Validate CDS Hooks Compliance

The sandbox validates that responses meet the CDS Hooks specification:

```python
from healthchain.sandbox import SandboxClient

client = SandboxClient(
    url="http://localhost:8000/cds-services/patient-alerts",
    workflow="patient-view"
)

# Enable strict validation
client.validate_responses = True

responses = client.send_requests()

# Check for validation errors
for response in responses:
    if response.validation_errors:
        print(f"Validation errors: {response.validation_errors}")
```

## Testing Different Hooks

Test different CDS Hooks workflows:

```python
# Test order-select hook
order_client = SandboxClient(
    url="http://localhost:8000/cds-services/drug-interactions",
    workflow="order-select"
)

# Test order-sign hook
sign_client = SandboxClient(
    url="http://localhost:8000/cds-services/order-review",
    workflow="order-sign"
)
```

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

client = SandboxClient(
    url="http://localhost:8000/cds-services/patient-alerts",
    workflow="patient-view"
)
```

### Inspect Request/Response

```python
response = client.send_single_request(patient_data)
print("Request sent:", response.request_body)
print("Response received:", response.json())
```

## What's Next

Your service is tested and working! Learn about [production deployment](next-steps.md) and extending your CDS service.
