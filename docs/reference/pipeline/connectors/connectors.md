# Connectors

Connectors transform your data into a format that can be understood by healthcare systems such as EHRs. They allow your pipelines to work directly with data in HL7 interoperability standard formats, such as [CDA](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) or [FHIR](https://hl7.org/fhir/), without the headache of parsing and validating the data yourself.

Connectors are what give you the power to build *end-to-end* pipelines that interact with real-time healthcare systems.

## Available connectors

Connectors make certain assumptions about the data they receive depending on the use case to convert it to an appropriate internal data format and container.

Some connectors require the same instance to be used for both input and output, while others may be input or output only.

| Connector | Input | Output | Internal Data Representation | Access it by... | Same instance I/O? |
|-----------|-------|--------|-------------------------|----------------|--------------------------|
| [**CdaConnector**](cdaconnector.md) | `CdaRequest` :material-arrow-right: `Document` | `Document` :material-arrow-right: `CdaRequest` | [**CcdData**](../../../api/data_models.md#healthchain.models.data.ccddata.CcdData) | `.ccd_data` | ✅ |
| [**CdsFhirConnector**](cdsfhirconnector.md) | `CDSRequest` :material-arrow-right: `Document` | `Document` :material-arrow-right: `CdsResponse` | [**CdsFhirData**](../../../api/data_models.md#healthchain.models.data.cdsfhirdata.CdsFhirData) | `.fhir_resources` | ✅ |

!!! example "CdaConnector Example"
    The `CdaConnector` expects a `CdaRequest` object as input and outputs a `CdaResponse` object. The connector converts the input data into a `Document` object because CDAs are usually represented as a document object.

    This `Document` object contains a `.ccd_data` attribute, which stores the structured data from the CDA document in a `CcdData` object. Any free-text notes are stored in the `Document.text` attribute.

    Because CDAs are annotated documents, the same `CdaConnector` instance must be used for both input and output operations in the pipeline.

## Use Cases
Each connector can be mapped to a specific use case in the sandbox module.

| Connector | Use Case |
|-----------|----------|
| `CdaConnector` | [**Clinical Documentation**](../../sandbox/use_cases/clindoc.md) |
| `CdsFhirConnector` | [**Clinical Decision Support**](../../sandbox/use_cases/cds.md) |

## Adding connectors to your pipeline

To add connectors to your pipeline, use the `.add_input()` and `.add_output()` methods.

```python
from healthchain.pipeline import Pipeline
from healthchain.io import CdaConnector

pipeline = Pipeline()
# In this example, we're using the same connector instance for input and output
cda_connector = CdaConnector()

pipeline.add_input(cda_connector)
pipeline.add_output(cda_connector)
```

Connectors are currently intended for development and testing purposes only. They are not production-ready, although this is something we want to work towards on our long-term roadmap. If there is a specific connector you would like to see, please feel free to [open an issue](https://github.com/dotimplement/healthchain/issues) or [contact us](https://discord.gg/UQC6uAepUz)!
