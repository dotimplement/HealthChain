# Quickstart

After [installing HealthChain](installation.md), get up to speed quickly with the core components before diving further into the [full documentation](reference/index.md)!

## Core Components

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

HealthChain comes with a few pre-built components, but you can also easily add your own. You can find more details on the [Components](./reference/pipeline/component.md) and [Models](./reference/pipeline/models/models.md) documentation pages.

Add components to your pipeline with the `.add_node()` method and compile with `.build()`.

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components import TextPreProcessor, Model, TextPostProcessor
from healthchain.io import Document

pipeline = Pipeline[Document]()

pipeline.add_node(TextPreProcessor())
pipeline.add_node(Model(model_path="path/to/model"))
pipeline.add_node(TextPostProcessor())

pipe = pipeline.build()

doc = Document("Patient presents with hypertension.")
output = pipe(doc)
```

Let's go one step further! You can use [Connectors](./reference/pipeline/connectors/connectors.md) to work directly with [CDA](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) and [FHIR](https://hl7.org/fhir/) data received from healthcare system APIs. Add Connectors to your pipeline with the `.add_input()` and `.add_output()` methods.

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components import Model
from healthchain.io import CdaConnector
from healthchain.models import CdaRequest

pipeline = Pipeline()
cda_connector = CdaConnector()

pipeline.add_input(cda_connector)
pipeline.add_node(Model(model_path="path/to/model"))
pipeline.add_output(cda_connector)

pipe = pipeline.build()

cda_data = CdaRequest(document="<CDA XML content>")
output = pipe(cda_data)
```

#### 3. Use Prebuilt Pipelines

Prebuilt pipelines are pre-configured collections of Components, Models, and Connectors. They are built for specific use cases, offering the highest level of abstraction. This is the easiest way to get started if you already know the use case you want to build for.

For a full list of available prebuilt pipelines and details on how to configure and customize them, see the [Pipelines](./reference/pipeline/pipeline.md) documentation page.

```python
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest

# Load from pre-built chain
chain = ChatPromptTemplate.from_template("Summarize: {text}") | ChatOpenAI()
pipeline = MedicalCodingPipeline.load(chain, source="langchain")

# Or load from model ID
pipeline = MedicalCodingPipeline.from_model_id("DISLab/SummLlama3-8B", source="huggingface")

# Or load from local model
pipeline = MedicalCodingPipeline.from_local_model("./path/to/model", source="spacy")

cda_data = CdaRequest(document="<CDA XML content>")
output = pipeline(cda_data)
```

### Sandbox 🧪
Once you've built your pipeline, you might want to experiment with how it interacts with different healthcare systems. A sandbox helps you stage and test the end-to-end workflow of your pipeline application where real-time EHR integrations are involved.

Running a sandbox will start a [FastAPI](https://fastapi.tiangolo.com/) server with pre-defined standardized endpoints and create a sandboxed environment for you to interact with your application.

To create a sandbox, initialize a class that inherits from a type of [UseCase](./reference/sandbox/use_cases/use_cases.md) and decorate it with the `@hc.sandbox` decorator.

Every sandbox also requires a **client** function marked by `@hc.ehr` and a **service** function marked by `@hc.api`. A **workflow** must be specified when creating an EHR client.

[(Full Documentation on Sandbox and Use Cases)](./reference/sandbox/sandbox.md)

```python
import healthchain as hc

from healthchain.use_cases import ClinicalDocumentation
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest, CdaResponse, CcdData

@hc.sandbox
class MyCoolSandbox(ClinicalDocumentation):
    def __init__(self) -> None:
        # Load your pipeline
        self.pipeline = MedicalCodingPipeline.from_local_model(
            "./path/to/model", source="spacy"
        )

    @hc.ehr(workflow="sign-note-inpatient")
    def load_data_in_client(self) -> CcdData:
        # Load your data
        with open('/path/to/data.xml', "r") as file:
          xml_string = file.read()

        return CcdData(cda_xml=xml_string)

    @hc.api
    def my_service(self, request: CdaRequest) -> CdaResponse:
        # Run your pipeline
        results = self.pipeline(request)
        return results

if __name__ == "__main__":
    clindoc = MyCoolSandbox()
    clindoc.start_sandbox()
```

## Deploy sandbox locally with FastAPI 🚀

To run your sandbox:

```bash
healthchain run my_sandbox.py
```

This will start a server by default at `http://127.0.0.1:8000`, and you can interact with the exposed endpoints at `/docs`. Data generated from your sandbox runs is saved at `./output/` by default.

## Utilities ⚙️
### Data Generator

You can use the data generator to generate synthetic data for your sandbox runs.

The `.generate()` is dependent on use case and workflow. For example, `CdsDataGenerator` will generate synthetic [FHIR](https://hl7.org/fhir/) data suitable for the workflow specified by the use case.

We're working on generating synthetic [CDA](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) data. If you're interested in contributing, please [reach out](https://discord.gg/UQC6uAepUz)!

[(Full Documentation on Data Generators)](./reference/utilities/data_generator.md)

=== "Within client"
    ```python
    import healthchain as hc

    from healthchain.use_cases import ClinicalDecisionSupport
    from healthchain.models import CdsFhirData
    from healthchain.data_generators import CdsDataGenerator

    @hc.sandbox
    class MyCoolSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            self.data_generator = CdsDataGenerator()

        @hc.ehr(workflow="patient-view")
        def load_data_in_client(self) -> CdsFhirData:
            data = self.data_generator.generate()
            return data

        @hc.api
        def my_server(self, request) -> None:
            pass
    ```


=== "On its own"
    ```python
    from healthchain.data_generators import CdsDataGenerator
    from healthchain.workflow import Workflow

    # Initialise data generator
    data_generator = CdsDataGenerator()

    # Generate FHIR resources for use case workflow
    data_generator.set_workflow(Workflow.encounter_discharge)
    data = data_generator.generate()

    print(data.model_dump())

    # {
    #    "prefetch": {
    #        "entry": [
    #            {
    #                "resource": ...
    #            }
    #        ]
    #    }
    #}
    ```

## Going further ✨
Check out our [Cookbook](cookbook/index.md) section for more worked examples! HealthChain is still in its early stages, so if you have any questions please feel free to reach us on [Github](https://github.com/dotimplement/HealthChain/discussions) or [Discord](https://discord.gg/UQC6uAepUz).
