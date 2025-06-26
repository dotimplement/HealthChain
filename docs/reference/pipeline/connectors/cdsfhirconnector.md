# CDS FHIR Connector

The `CdsFhirConnector` handles FHIR data in the context of Clinical Decision Support (CDS) services, specifically using the [CDS Hooks specification](https://cds-hooks.org/).

[(Full Documentation on Clinical Decision Support)](../../gateway/cdshooks.md)

## Input and Output

| Input | Output | Access |
|-------|--------|-----------|
| [**CDSRequest**](../../../api/use_cases.md#healthchain.models.requests.cdsrequest.CDSRequest) | [**CDSResponse**](../../../api/use_cases.md#healthchain.models.responses.cdsresponse.CDSResponse) | `Document.fhir.prefetch_resources` |


## Usage

```python
from healthchain.io import CdsFhirConnector, Document
from healthchain.models import CDSRequest
from healthchain.pipeline import Pipeline

# Create a pipeline with CdsFhirConnector
pipeline = Pipeline()

cds_fhir_connector = CdsFhirConnector(hook_name="patient-view")
pipeline.add_input(cds_fhir_connector)
pipeline.add_output(cds_fhir_connector)

# Example CDS request
cds_request = CDSRequest(
    hook="patient-view",
    hookInstance="d1577c69-dfbe-44ad-ba6d-3e05e953b2ea",
    context={
        "userId": "Practitioner/123",
        "patientId": "Patient/456"
    },
    prefetch={
        "patient": {
            "resourceType": "Patient",
            "id": "456",
            "name": [{"family": "Doe", "given": ["John"]}],
            "birthDate": "1970-01-01"
        }
    }
)

# Accessing FHIR data inside a pipeline node
@pipeline.add_node
def example_pipeline_node(document: Document) -> Document:
    print(document.fhir.get_prefetch_resources("patient"))
    return document

# Execute the pipeline
pipe = pipeline.build()
cds_response = pipe(cds_request)
# Output: CdsResponse with cards...
```

## Accessing data inside your pipeline

Data parsed from the CDS request is stored in the `Document.fhir.prefetch_resources` attribute as a dictionary of FHIR resources corresponding to the keys in the `prefetch` field of the `CDSRequest`. For more information on the `prefetch` field, check out the [CDS Hooks specification on providing FHIR resources to a CDS service](https://cds-hooks.org/specification/current/#providing-fhir-resources-to-a-cds-service).

### Example Prefetch

```json
{
    "patient": {
        "resourceType": "Patient",
        "id": "123",
        "name": [{"family": "Doe", "given": ["John"]}],
        "birthDate": "1970-01-01"
    },
    "condition": // Condition FHIR resource...
    "document": // DocumentReference FHIR resource...
}
```
