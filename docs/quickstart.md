# Quickstart

After [installing HealthChain](installation.md), get up to speed quickly with the core components before diving further into the [full documentation](reference/index.md)!
HealthChain has three main components:

- **Gateway:** Connect to multiple healthcare systems with a single API.
- **Pipelines:** Easily build data processing pipelines for both clinical text and [FHIR](https://www.hl7.org/fhir/) data.
- **InteropEngine:** Seamlessly convert between data formats like [FHIR](https://www.hl7.org/fhir/), [HL7 CDA](https://www.hl7.org/implement/standards/product_brief.cfm?product_id=7), and [HL7v2](https://www.hl7.org/implement/standards/product_brief.cfm?product_id=185).


## Core Components 🧩

### Gateway 🔌

The [**HealthChainAPI**](./reference/gateway/api.md) provides a unified interface for connecting your AI application and models to multiple healthcare systems through a single API. It automatically handles [FHIR API](https://www.hl7.org/fhir/http.html), [CDS Hooks](https://cds-hooks.org/), and [SOAP/CDA protocols](https://www.hl7.org/implement/standards/product_brief.cfm?product_id=7) with [OAuth2 authentication](https://oauth.net/2/).

[(Full Documentation on Gateway)](./reference/gateway/gateway.md)

```python
from healthchain.gateway import HealthChainAPI, FHIRGateway
from fhir.resources.patient import Patient

# Create your healthcare application
app = HealthChainAPI(title="My Healthcare AI App")

# Connect to multiple FHIR servers
fhir = FHIRGateway()
fhir.add_source("epic", "fhir://fhir.epic.com/r4?client_id=...")
fhir.add_source("medplum", "fhir://api.medplum.com/fhir/R4/?client_id=...")

# Add AI transformations to FHIR data
@fhir.transform(Patient)
def enhance_patient(id: str, source: str = None) -> Patient:
    patient = fhir.read(Patient, id, source)
    # Your AI logic here
    patient.active = True
    fhir.update(patient, source)
    return patient

# Register and run
app.register_gateway(fhir)

# Available at: GET /fhir/transform/Patient/123?source=epic
```

### Pipeline 🛠️

HealthChain [**Pipelines**](./reference/pipeline/pipeline.md) provide a flexible way to build and manage processing pipelines for NLP and ML tasks that can easily integrate with electronic health record (EHR) systems.

You can build pipelines with three different approaches:

#### 1. Quick Inline Functions

For quick experiments, start by picking the right [**Container**](./reference/io/containers/containers.md) when you initialize your pipeline (e.g. `Pipeline[Document]()` for clinical text).

Containers make your pipeline FHIR-native by loading and transforming your data (free text, EHR resources, etc.) into structured FHIR-ready formats. Just add your processing functions with `@add_node`, compile with `.build()`, and your pipeline is ready to process FHIR data end-to-end.

[(Full Documentation on Containers)](./reference/io/containers/containers.md)

```python
from healthchain.pipeline import Pipeline
from healthchain.io import Document
from healthchain.fhir import create_condition

pipeline = Pipeline[Document]()

@pipeline.add_node
def extract_diabetes(doc: Document) -> Document:
    """Adds a FHIR Condition for diabetes if mentioned in the text."""
    if "diabetes" in doc.text.lower():
        condition = create_condition(
            code="73211009",
            display="Diabetes mellitus",
        )
        doc.fhir.problem_list.append(condition)

    return doc

pipe = pipeline.build()

doc = Document("Patient has a history of diabetes.")
doc = pipe(doc)

print(doc.fhir.problem_list)  # FHIR Condition
```

#### 2. Build With Components and Adapters

[**Components**](./reference/) are reusable, stateful classes that encapsulate specific processing logic, model loading, or configuration for your pipeline. Use them to organize complex workflows, handle model state, or integrate third-party libraries with minimal setup.

HealthChain provides a set of ready-to-use [**NLP Integrations**](./reference/pipeline/integrations/integrations.md) for common clinical NLP and ML tasks, and you can easily implement your own.

[(Full Documentation on Components)](./reference/pipeline/components/components.md)

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components import TextPreProcessor, SpacyNLP, TextPostProcessor
from healthchain.io import Document

pipeline = Pipeline[Document]()

pipeline.add_node(TextPreProcessor())
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
pipeline.add_node(TextPostProcessor())

pipe = pipeline.build()

doc = Document("Patient presents with hypertension.")
output = pipe(doc)
```

You can process legacy healthcare data formats too. [**Adapters**](./reference/io/adapters/adapters.md) convert between healthcare formats like [CDA](https://www.hl7.org/implement/standards/product_brief.cfm?product_id=7) and your pipeline — just parse, process, and format without worrying about low-level data conversion.

[(Full Documentation on Adapters)](./reference/io/adapters/adapters.md)

```python
from healthchain.io import CdaAdapter
from healthchain.models import CdaRequest

# Use adapter for format conversion
adapter = CdaAdapter()
cda_request = CdaRequest(document="<CDA XML content>")

# Parse, process, format
doc = adapter.parse(cda_request)
processed_doc = pipe(doc)
output = adapter.format(processed_doc)
```

#### 3. Use Prebuilt Pipelines

Prebuilt pipelines are the fastest way to jump into healthcare AI with minimal setup: just load and run. Each pipeline bundles best-practice components and models for common clinical tasks (like coding or summarization) and handles all FHIR/CDA conversion for you. Easily customize or extend pipelines by adding/removing components, or swap models as needed.

[(Full Documentation on Pipelines)](./reference/pipeline/pipeline.md#prebuilt-)

```python
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest

# Or load from local model
pipeline = MedicalCodingPipeline.from_local_model("./path/to/model", source="spacy")

cda_request = CdaRequest(document="<CDA XML content>")
output = pipeline.process_request(cda_request)
```

### Interoperability 🔄

The HealthChain Interoperability module provides tools for converting between different healthcare data formats, including FHIR, CDA, and HL7v2 messages.

[(Full Documentation on Interoperability Engine)](./reference/interop/interop.md)

```python
from healthchain.interop import create_interop, FormatType

# Uses bundled configs - basic CDA ↔ FHIR conversion
engine = create_interop()

# Load a CDA document
with open("tests/data/test_cda.xml", "r") as f:
    cda_xml = f.read()

# Convert CDA XML to FHIR resources
fhir_resources = engine.to_fhir(cda_xml, src_format=FormatType.CDA)

# Convert FHIR resources back to CDA
cda_document = engine.from_fhir(fhir_resources, dest_format=FormatType.CDA)
```


## Utilities ⚙️

### Sandbox Client 🧪

Use [**SandboxClient**](./reference/utilities/sandbox.md) to quickly test your app against real-world EHR scenarios like CDS Hooks or Clinical Documentation Improvement (CDI) workflows. Load test datasets, send requests to your service, and validate responses in a few lines of code.

[(Full Documentation on Sandbox)](./reference/utilities/sandbox.md)

#### Workflows

A [**workflow**](./reference/utilities/sandbox.md#workflow-protocol-compatibility) represents a specific event in an EHR system that triggers your service (e.g., `patient-view` when opening a patient chart, `encounter-discharge` when discharging a patient).

Workflows determine the request structure, required FHIR resources, and validation rules. Different workflows are compatible with different protocols:

| Workflow Type                      | Protocol   | Example Workflows                                      |
|-------------------------------------|------------|--------------------------------------------------------|
| **CDS Hooks**                      | REST       | `patient-view`, `order-select`, `order-sign`, `encounter-discharge` |
| **Clinical Documentation**          | SOAP       | `sign-note-inpatient`, `sign-note-outpatient`          |


#### Available Dataset Loaders

[**Dataset Loaders**](./reference/utilities/sandbox.md#dataset-loaders) are shortcuts for loading common clinical test datasets from file. Currently available:

| Dataset Key        | Description                                 | FHIR Version | Source                                                                                  | Download Link                                                                                  |
|--------------------|---------------------------------------------|--------------|-----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| `mimic-on-fhir`    | **MIMIC-IV on FHIR Demo Dataset**        | R4           | [PhysioNet Project](https://physionet.org/content/mimic-iv-fhir-demo/2.1.0/)                  | [Download ZIP](https://physionet.org/content/mimic-iv-fhir-demo/get-zip/2.1.0/) (49.5 MB)      |
| `synthea-patient`  | **Synthea FHIR Patient Records**    | R4           | [Synthea Downloads](https://synthea.mitre.org/downloads)                                  | [Download ZIP](https://arc.net/l/quote/hoquexhy) (100 Sample, 36 MB)                           |


```python
from healthchain.sandbox import list_available_datasets

# See all registered datasets with descriptions
datasets = list_available_datasets()
print(datasets)
```

#### Basic Usage

```python
from healthchain.sandbox import SandboxClient

# Initialize client with your service URL and workflow
client = SandboxClient(
    url="http://localhost:8000/cds/encounter-discharge",
    workflow="encounter-discharge"
)

# Load test data from a registered dataset
client.load_from_registry(
    "synthea-patient",
    data_dir="./data/synthea",
    resource_types=["Condition", "DocumentReference"],
    sample_size=3
)

# Optionally inspect before sending
client.preview_requests()  # See what will be sent
client.get_status()        # Check client state

# Send requests to your service
responses = client.send_requests()
```

For clinical documentation workflows using SOAP/CDA:

```python
# Use context manager for automatic result saving
with SandboxClient(
    url="http://localhost:8000/notereader/ProcessDocument",
    workflow="sign-note-inpatient",
    protocol="soap"
) as client:
    client.load_from_path("./cookbook/data/notereader_cda.xml")
    responses = client.send_requests()
    # Results automatically saved to ./output/ on success
```

### FHIR Helpers 🔥

Use `healthchain.fhir` helpers to quickly create and manipulate FHIR resources (like `Condition`, `Observation`, etc.) in your code, ensuring they’re standards-compliant with minimal boilerplate.

[(Full Documentation on FHIR Helpers)](./reference/utilities/fhir_helpers.md)

```python
from healthchain.fhir import create_condition

condition = create_condition(
    code="38341003",
    display="Hypertension",
    system="http://snomed.info/sct",
    subject="Patient/Foo",
    clinical_status="active"
)
```

## Going further ✨
Check out our [Cookbook](cookbook/index.md) section for more worked examples! HealthChain is still in its early stages, so if you have any questions please feel free to reach us on [Github](https://github.com/dotimplement/HealthChain/discussions) or [Discord](https://discord.gg/UQC6uAepUz).
