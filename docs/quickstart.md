# Quickstart

After [installing HealthChain](installation.md), get up to speed quickly with the core components before diving further into the [full documentation](reference/index.md)!

HealthChain provides three core tools for healthcare AI integration: **Gateway** for connecting to multiple healthcare systems, **Pipelines** for FHIR-native AI workflows, and **InteropEngine** for healthcare data format conversion between FHIR, CDA, and HL7v2.

## Core Components

### HealthChainAPI Gateway 🔌

The HealthChainAPI provides a unified interface for connecting your AI models to multiple healthcare systems through a single API. Handle FHIR, CDS Hooks, and SOAP/CDA protocols with OAuth2 authentication.

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

HealthChain Pipelines provide a flexible way to build and manage processing pipelines for NLP and ML tasks that can easily integrate with electronic health record (EHR) systems.

You can build pipelines with three different approaches:

#### 1. Build Your Own Pipeline with Inline Functions

This is the most flexible approach, ideal for quick experiments and prototyping. Initialize a pipeline type hinted with the container type you want to process, then add components to your pipeline with the `@add_node` decorator.

Compile the pipeline with `.build()` to use it.

```python
from healthchain.pipeline import Pipeline
from healthchain.io import Document

nlp_pipeline = Pipeline[Document]()

@nlp_pipeline.add_node
def tokenize(doc: Document) -> Document:
    doc.tokens = doc.text.split()
    return doc

@nlp_pipeline.add_node
def pos_tag(doc: Document) -> Document:
    doc.pos_tags = ["NOUN" if token[0].isupper() else "VERB" for token in doc.tokens]
    return doc

nlp = nlp_pipeline.build()

doc = Document("Patient has a fracture of the left femur.")
doc = nlp(doc)

print(doc.tokens)
print(doc.pos_tags)

# ['Patient', 'has', 'fracture', 'of', 'left', 'femur.']
# ['NOUN', 'VERB', 'VERB', 'VERB', 'VERB', 'VERB']
```

#### 2. Build Your Own Pipeline with Components, Models, and Connectors

Components are stateful - they're classes instead of functions. They can be useful for grouping related processing steps together, setting configurations, or wrapping specific model loading steps.

HealthChain comes with a few pre-built components, but you can also easily add your own. You can find more details on the [Components](./reference/pipeline/components/components.md) and [Integrations](./reference/pipeline/integrations/integrations.md) documentation pages.

Add components to your pipeline with the `.add_node()` method and compile with `.build()`.

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

Let's go one step further! You can use [Adapters](./reference/pipeline/adapters/adapters.md) to work directly with [CDA](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) and [FHIR](https://hl7.org/fhir/) data received from healthcare system APIs. Adapters handle format conversion while keeping your pipeline pure ML processing.

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components import SpacyNLP
from healthchain.io import CdaAdapter
from healthchain.models import CdaRequest

pipeline = Pipeline()
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
pipe = pipeline.build()

# Use adapter for format conversion
adapter = CdaAdapter()
cda_request = CdaRequest(document="<CDA XML content>")

# Parse, process, format
doc = adapter.parse(cda_request)
processed_doc = pipe(doc)
output = adapter.format(processed_doc)
```

#### 3. Use Prebuilt Pipelines

Prebuilt pipelines are pre-configured collections of Components and Models optimized for specific healthcare AI use cases. They offer the highest level of abstraction and are the easiest way to get started.

For a full list of available prebuilt pipelines and details on how to configure and customize them, see the [Pipelines](./reference/pipeline/pipeline.md) documentation page.

```python
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest

# Load from pre-built chain
chain = ChatPromptTemplate.from_template("Summarize: {text}") | ChatOpenAI()
pipeline = MedicalCodingPipeline.load(chain, source="langchain")

# Or load from model ID
pipeline = MedicalCodingPipeline.from_model_id("facebook/bart-large-cnn", source="huggingface")

# Or load from local model
pipeline = MedicalCodingPipeline.from_local_model("./path/to/model", source="spacy")

cda_request = CdaRequest(document="<CDA XML content>")
output = pipeline.process_request(cda_request)
```

### Interoperability 🔄

The HealthChain Interoperability module provides tools for converting between different healthcare data formats, including HL7 FHIR, HL7 CDA, and HL7v2 messages.

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

### Sandbox Testing

Test your AI applications in realistic healthcare contexts with `SandboxClient` for CDS Hooks and clinical documentation workflows.

[(Full Documentation on Sandbox)](./reference/utilities/sandbox.md)

```python
from healthchain.sandbox import SandboxClient

# Create client and load test data
client = SandboxClient(
    api_url="http://localhost:8000",
    endpoint="/cds/cds-services/my-service",
    workflow="encounter-discharge"
)

# Load from datasets or files
client.load_from_registry("synthea", num_patients=5)
responses = client.send_requests()
```

### FHIR Helpers

The `fhir` module provides a set of helper functions for working with FHIR resources.

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

[(Full Documentation on FHIR Helpers)](./reference/utilities/fhir_helpers.md)

### Data Generator

You can use the data generator to generate synthetic FHIR data for testing.

The `CdsDataGenerator` generates synthetic [FHIR](https://hl7.org/fhir/) data as [Pydantic](https://docs.pydantic.dev/) models suitable for different CDS workflows. Use it standalone or with `SandboxClient.load_free_text()` to include text-based data.

[(Full Documentation on Data Generators)](./reference/utilities/data_generator.md)

```python
from healthchain.sandbox.generators import CdsDataGenerator
from healthchain.sandbox.workflows import Workflow

# Initialize data generator
data_generator = CdsDataGenerator()

# Generate FHIR resources for specific workflow
data_generator.set_workflow(Workflow.encounter_discharge)
data = data_generator.generate_prefetch()

print(data.model_dump())

# {
#    "prefetch": {
#        "encounter": {
#            "resourceType": ...
#        }
#    }
# }
```

## Going further ✨
Check out our [Cookbook](cookbook/index.md) section for more worked examples! HealthChain is still in its early stages, so if you have any questions please feel free to reach us on [Github](https://github.com/dotimplement/HealthChain/discussions) or [Discord](https://discord.gg/UQC6uAepUz).
