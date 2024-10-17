# CDS FHIR Connector

The `CdsFhirConnector` handles FHIR data in the context of Clinical Decision Support (CDS) services, serving as both an input and output connector in the pipeline.

Note that this is not meant to be used as a generic FHIR connector, but specifically designed for use with the [CDS Hooks specification](https://cds-hooks.org/).

[(Full Documentation on Clinical Decision Support)](../../sandbox/use_cases/cds.md)

## Usage

```python
from healthchain.io import CdsFhirConnector, Document
from healthchain.models import CDSRequest
from healthchain.pipeline import Pipeline

# Create a pipeline with CdsFhirConnector
pipeline = Pipeline()

cds_fhir_connector = CdsFhirConnector()
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

# Example 1: Simple pipeline execution
pipe = pipeline.build()
cds_response = pipe(cds_request)
print(cds_response)
# Output: CDSResponse with cards...

# Example 2: Accessing FHIR data inside a pipeline node
@pipeline.add_node
def example_pipeline_node(document: Document) -> Document:
    print(document.fhir_resources)
    return document

pipe = pipeline.build()
cds_response = pipe(cds_request)
# Output: CdsFhirData object...

```

## Accessing data inside your pipeline

Data parsed from the FHIR resources is stored in the `Document.fhir_resources` attribute as a `CdsFhirData` object, as shown in the example above.

[(CdsFhirData Reference)](../../../api/data_models.md#healthchain.models.data.cdsfhirdata)
