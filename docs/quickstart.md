# Quickstart

After [installing HealthChain](installation.md), get up to speed quickly with the core components before diving further into the [full documentation](reference/index.md)!

## Core Components

### Pipeline 🛠️

The `Pipeline` module in HealthChain provides a flexible way to build and manage processing pipelines for NLP and ML tasks that can easily interface with
parsers and connectors to integrate with electronic health record (EHR) systems.

You can build pipelines with three different approaches:

#### 1. Build Your Own Pipeline with Inline Functions

This is the most flexible approach, ideal for quick experiments and prototyping. Initialize a pipeline type hinted with the container type you want to process, then add components to your pipeline with the `@add` decorator.

Compile the pipeline with `.build()` to use it.

```python
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document

nlp_pipeline = Pipeline[Document]()

@nlp_pipeline.add
def tokenize(doc: Document) -> Document:
    doc.tokens = doc.text.split()
    return doc

@nlp_pipeline.add
def pos_tag(doc: Document) -> Document:
    # Dummy POS tagging
    doc.pos_tags = ["NOUN" if token[0].isupper() else "VERB" for token in doc.tokens]
    return doc

# Build and use the pipeline
nlp = nlp_pipeline.build()
doc = Document("Patient has a fracture of the left femur.")
doc = nlp(doc)

print(doc.tokens)
print(doc.pos_tags)

# ['Patient', 'has', 'fracture', 'of', 'left', 'femur.']
# ['NOUN', 'VERB', 'VERB', 'VERB', 'VERB', 'VERB']
```

#### 2. Build Your Own Pipeline with Components and Models

Components are stateful - they're classes instead of functions. They can be useful for grouping related processing steps together, or wrapping specific models.

HealthChain comes with a few pre-built components, but you can also easily add your own. You can find more details on the [Components](./reference/pipeline/component.md) and [Models](./reference/pipeline/models/models.md) documentation pages.

Add components to your pipeline with the `.add()` method.

```python
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document
from healthchain.pipeline.components import TextPreProcessor, Model, TextPostProcessor

pipeline = Pipeline[Document]()

pipeline.add(TextPreProcessor())
pipeline.add(Model(model_path="path/to/model"))
pipeline.add(TextPostProcessor())

pipe = pipeline.build()
doc = Document("Patient presents with hypertension.")
doc = pipe(doc)
```

#### 3. Use Prebuilt Pipelines

Prebuilt pipelines are pre-configured collections of `Components` and `Models`. They are configured for specific use cases, offering the highest level of abstraction. This is the easiest way to get started if you already know the use case you want to build for.

For a full list of available prebuilt pipelines and details on how to configure and customize them, see the [Pipelines](./reference/pipeline/pipeline.md) documentation page.

```python
from healthchain.pipeline import MedicalCodingPipeline

pipeline = MedicalCodingPipeline.load("./path/to/model")
pipe = pipeline.build()

doc = Document("Patient diagnosed with myocardial infarction.")
doc = pipe(doc)
```

### Sandbox 🧪
Once you've built your pipeline, you might want to experiment with how you want your pipeline to interact with different health systems. A sandbox helps you stage and test the end-to-end workflow of your pipeline application where real-time EHR integrations are involved.

Running a sandbox will start a `FastAPI` server with standardized API endpoints and create a sandboxed environment for you to interact with your application.

To create a sandbox, initialize a class that inherits from a type of `UseCase` and decorate it with the `@hc.sandbox` decorator.

Every sandbox also requires a **client** function marked by `@hc.ehr` and a **service** function marked by `@hc.api`. A **workflow** must be specified when creating an EHR client.

[(Full Documentation on Sandbox and Use Cases)](./reference/sandbox/sandbox.md)

```python
import healthchain as hc

from healthchain.use_cases import ClinicalDocumentation
from healthchain.pipeline import MedicalCodingPipeline

@hc.sandbox
class MyCoolSandbox(ClinicalDocumentation):
    def __init__(self) -> None:
        # Load your pipeline
        pipeline = MedicalCodingPipeline.load("./path/to/model")
        self.pipe = self.pipeline.build()

    @hc.ehr(workflow="sign-note-inpatient")
    def load_data_in_client(self) -> CcdData:
        # Load your data
        with open('/path/to/data.xml', "r") as file:
          xml_string = file.read()

        return CcdData(cda_xml=xml_string)

    @hc.api
    def my_service(self, ccd_data: CcdData) -> CcdData:
        # Run your pipeline
        results = self.pipeline(ccd_data)
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

## Inspect generated data in Streamlit 🎈
The streamlit dashboard is run separately and is currently purely for visualisation purposes.

You need to install streamlit separately first:
```bash
pip install streamlit
```
Then run:

```bash
cd streamlist_demo
streamlit run app.py
```

## Utilities ⚙️
### Data Generator

You can use the data generator to generate synthetic data for your sandbox runs.

The `.generate()` is dependent on use case and workflow. For example, `CdsDataGenerator` will generate synthetic [FHIR](https://build.fhir.org/) data suitable for the workflow specified by the use case.

We're currently working on generating synthetic [CDA](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) data. If you're interested in contributing, please [reach out](https://discord.gg/UQC6uAepUz)!

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
