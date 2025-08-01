# Connectors (Legacy)

> **⚠️ Deprecated:** Connectors are being replaced by the new [Adapter pattern](../adapters/adapters.md). For new projects, use Adapters for cleaner separation between ML processing and healthcare format handling.

Connectors transform your data into a format that can be understood by healthcare systems such as EHRs. They allow your pipelines to work directly with data in HL7 interoperability standard formats, such as [CDA](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) or [FHIR](https://hl7.org/fhir/), without the headache of parsing and validating the data yourself.

**For new projects, consider using [Adapters](../adapters/adapters.md) instead**, which provide explicit control over data conversion and enable pure `Document → Document` pipeline processing.

## Migration to Adapters

| Legacy Connector | New Adapter | Migration Guide |
|------------------|-------------|-----------------|
| `CdaConnector` | [`CdaAdapter`](../adapters/cdaadapter.md) | Remove `add_input()` and `add_output()` calls, use explicit `parse()` and `format()` methods |
| `CdsFhirConnector` | [`CdsFhirAdapter`](../adapters/cdsfhiradapter.md) | Remove `add_input()` and `add_output()` calls, use explicit `parse()` and `format()` methods |

### Quick Migration Example

**Before (Connectors):**
```python
pipeline.add_input(CdaConnector())
pipeline.add_output(CdaConnector())
response = pipeline(cda_request)
```

**After (Adapters):**
```python
adapter = CdaAdapter()
doc = adapter.parse(cda_request)
doc = pipeline(doc)
response = adapter.format(doc)
```

[→ Full Adapter Documentation](../adapters/adapters.md)

## Available connectors (Legacy)

Connectors parse data from a specific format into FHIR resources and store them in a `Document` container.

([Document API Reference](../../../api/containers.md#healthchain.io.containers.document.Document))

Some connectors require the same instance to be used for both input and output as they respond to a synchronous call, while others may be input or output only.

| Connector | FHIR Resources | Access | Same instance I/O? |
|-----------|-------------------------|----------------|--------------------------|
| [**CdaConnector**](cdaconnector.md) | [**DocumentReference**](https://www.hl7.org/fhir/documentreference.html) | `Document.text`, `Document.fhir.problem_list`, `Document.fhir.medication_list`, `Document.fhir.allergy_list` | ✅ |
| [**CdsFhirConnector**](cdsfhirconnector.md) | [**Any FHIR Resource**](https://www.hl7.org/fhir/resourcelist.html) | `Document.fhir.get_prefetch_resources()` | ✅ |


## Use Cases
Each connector can be mapped to a specific use case in the sandbox module.

| Connector | Use Case |
|-----------|----------|
| `CdaConnector` | [**Clinical Documentation**](../../gateway/soap_cda.md) |
| `CdsFhirConnector` | [**Clinical Decision Support**](../../gateway/cdshooks.md) |

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

Connectors are currently intended for development and testing purposes only. They are not production-ready, although this is something we are working towards on our long-term roadmap. If there is a specific connector you would like to see, please feel free to [open an issue](https://github.com/dotimplement/healthchain/issues) or [contact us](https://discord.gg/UQC6uAepUz)!
