# CDA Connector

The `CdaConnector` handles Clinical Document Architecture (CDA) documents, serving as both an input and output connector in the pipeline. It parses CDA documents, extracting free-text notes and relevant structured clinical data into a `Document` object, and can return an annotated CDA document as output.

This connector is particularly useful for clinical documentation improvement (CDI) workflows where CDA documents need to be processed and updated with additional structured data.

[(Full Documentation on Clinical Documentation)](../../sandbox/use_cases/clindoc.md)

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
cda_request = CdaRequest(document="<CDA XML content>")

# Example 1: Simple pipeline execution
pipe = pipeline.build()
cda_response = pipe(cda_request)
print(cda_response)
# Output: CdaResponse(document='<Annotated CDA XML content>')

# Example 2: Accessing CDA data inside a pipeline node
@pipeline.add_node
def example_pipeline_node(document: Document) -> Document:
    print(document.ccd_data)
    return document

pipe = pipeline.build()
cda_response = pipe(cda_request)
# Output: CdaResponse object...
```

## Accessing data inside your pipeline

Data parsed from the CDA document is stored in the `Document.fhir` attribute as a `DocumentReference` FHIR resource, as shown in the example above.

## Configuration

The `overwrite` parameter in the `CdaConnector` constructor determines whether existing data in the document should be overwritten. This can be useful for readability with very long CDA documents when the receiving system does not require the full document.

```python
cda_connector = CdaConnector(overwrite=True)
```
