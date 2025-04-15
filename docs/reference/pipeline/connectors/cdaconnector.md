# CDA Connector

The `CdaConnector` parses CDA documents, extracting free-text notes and relevant structured clinical data into FHIR resources in the `Document` container, and returns an annotated CDA document as output. It will also extract the text from the note section of the document and store it in the `Document.text` attribute.

This connector is particularly useful for clinical documentation improvement (CDI) workflows where a document needs to be processed and updated with additional structured data.

[(Full Documentation on Clinical Documentation)](../../sandbox/use_cases/clindoc.md)


## Input and Output

| Input | Output | Access |
|-------|--------|-----------|
| [**CdaRequest**](../../../api/use_cases.md#healthchain.models.requests.cdarequest.CdaRequest) | [**CdaResponse**](../../../api/use_cases.md#healthchain.models.responses.cdaresponse.CdaResponse) | `Document.fhir.problem_list`, `Document.fhir.medication_list`, `Document.fhir.allergy_list`, `Document.text` |

## Usage

```python
from healthchain.io import CdaConnector, Document
from healthchain.models import CdaRequest
from healthchain.pipeline import Pipeline

# Create a pipeline with CdaConnector
pipeline = Pipeline()

cda_connector = CdaConnector()
pipeline.add_input(cda_connector)
pipeline.add_output(cda_connector)

# Example CDA request
cda_request = CdaRequest(document="<CDA>test</CDA>")

# Accessing CDA data inside a pipeline node
@pipeline.add_node
def example_pipeline_node(document: Document) -> Document:
    print(document.fhir.problem_list)
    print(document.text)
    return document

# Pipeline execution
pipe = pipeline.build()
cda_response = pipe(cda_request)
print(cda_response)
# Output: CdaResponse(document='<Annotated CDA XML content>')
```

## Accessing data inside your pipeline

Data parsed from the CDA document is converted into FHIR resources and stored in the `Document.fhir.bundle` attribute. The connector currently supports the following CDA section to FHIR resource mappings:

CDA section | FHIR resource | Document.fhir attribute
--- | --- | ---
Problem List | [Condition](https://www.hl7.org/fhir/condition.html) | `Document.fhir.problem_list`
Medication List | [MedicationStatement](https://www.hl7.org/fhir/medicationstatement.html) | `Document.fhir.medication_list`
Allergy List | [AllergyIntolerance](https://www.hl7.org/fhir/allergyintolerance.html) | `Document.fhir.allergy_list`
Note | [DocumentReference](https://www.hl7.org/fhir/documentreference.html) | `Document.fhir.bundle` (use `get_resources("DocumentReference")` to access)


## Configuration

Configure the directory of the CDA templates and configuration files through the `config_dir` parameter in the `CdaConnector` constructor.

```python
cda_connector = CdaConnector(config_dir="path/to/config/dir")
```
([Full Documentation on InteropEngine](../../interop/interop.md))
