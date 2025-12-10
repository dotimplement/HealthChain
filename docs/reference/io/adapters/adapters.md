# Adapters

Adapters handle conversion between healthcare data formats (CDA, FHIR) and HealthChain's internal `Document` objects. They enable clean separation between ML processing logic and healthcare format handling, making your pipelines more maintainable and testable.

Unlike the legacy connector pattern, adapters are used explicitly and provide clear control over data flow.

## Available adapters

Adapters parse data from specific healthcare formats into FHIR resources and store them in a `Document` container for processing.

([Document API Reference](../../../api/containers.md#healthchain.io.containers.document))

| Adapter | Input Format | Output Format | FHIR Resources | Document Access |
|---------|--------------|---------------|----------------|-----------------|
| [**CdaAdapter**](cdaadapter.md) | `CdaRequest` | `CdaResponse` | [**DocumentReference**](https://www.hl7.org/fhir/documentreference.html) | `Document.text`, `Document.fhir.problem_list`, `Document.fhir.medication_list`, `Document.fhir.allergy_list` |
| [**CdsFhirAdapter**](cdsfhiradapter.md) | `CDSRequest` | `CDSResponse` | [**Any FHIR Resource**](https://www.hl7.org/fhir/resourcelist.html) | `Document.fhir.get_prefetch_resources()` |

## Use Cases
Each adapter is designed for specific healthcare integration scenarios.

| Adapter | Use Case | Protocol |
|---------|----------|----------|
| `CdaAdapter` | [**Clinical Documentation**](../../gateway/soap_cda.md) | SOAP/CDA |
| `CdsFhirAdapter` | [**Clinical Decision Support**](../../gateway/cdshooks.md) | CDS Hooks/FHIR |

## Usage Patterns

### 1. Simple End-to-End Processing

Use prebuilt pipelines with the `process_request()` method for straightforward workflows:

```python
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest

pipeline = MedicalCodingPipeline.from_model_id("en_core_sci_sm", source="spacy")
cda_request = CdaRequest(document="<CDA XML content>")

# Adapter used internally
response = pipeline.process_request(cda_request)
```

### 2. Manual Adapter Control (Document Access)

Use adapters `parse()` and `format()` methods directly when you need access to the intermediate `Document` object:

```python
from healthchain.io import CdaAdapter
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest

pipeline = MedicalCodingPipeline.from_model_id("en_core_sci_sm", source="spacy")
adapter = CdaAdapter()

cda_request = CdaRequest(document="<CDA XML content>")

# Manual adapter control
doc = adapter.parse(cda_request)      # CdaRequest → Document
doc = pipeline(doc)                   # Document → Document (pure ML)

# Access extracted clinical data
print(f"Problems: {doc.fhir.problem_list}")
print(f"Medications: {doc.fhir.medication_list}")
print(f"Allergies: {doc.fhir.allergy_list}")

# Convert back to healthcare format
response = adapter.format(doc)        # Document → CdaResponse
```

For more details on the Document container, see [Document](../../io/containers/document.md).

## Adapter Configuration

### Custom Interop Engine

Both CDA and CDS adapters can be configured with custom interoperability engines. By default, the adapter uses the built-in InteropEngine with default CDA templates.

```python
from healthchain.io import CdaAdapter
from healthchain.interop import create_interop

# Custom engine with specific configuration
custom_engine = create_interop(config_dir="/path/to/custom/config")
adapter = CdaAdapter(engine=custom_engine)
```
For more information on the InteropEngine, see the [InteropEngine documentation](../../interop/interop.md).
