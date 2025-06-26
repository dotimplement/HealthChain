# Pipeline

HealthChain pipelines provide a simple interface to test, version, and connect your pipeline to common healthcare data standards, such as [CDA (Clinical Document Architecture)](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) and [FHIR (Fast Healthcare Interoperability Resources)](https://build.fhir.org/).

Depending on your need, you can either go top down, where you use prebuilt pipelines and customize them to your needs, or bottom up, where you build your own pipeline from scratch.

## Prebuilt 📦

HealthChain comes with a set of prebuilt pipelines that are out-of-the-box implementations of common healthcare data processing tasks:

| Pipeline | Container | Compatible Connector | Description | Example Use Case |
|----------|-----------|-----------|-------------|------------------|
| [**MedicalCodingPipeline**](./prebuilt_pipelines/medicalcoding.md) | `Document` | `CdaConnector` | An NLP pipeline that processes free-text clinical notes into structured data | Automatically generating SNOMED CT codes from clinical notes |
| [**SummarizationPipeline**](./prebuilt_pipelines/summarization.md) | `Document` | `CdsFhirConnector` | An NLP pipeline for summarizing clinical notes | Generating discharge summaries from patient history and notes |
| **QAPipeline** [TODO] | `Document` | N/A | A Question Answering pipeline suitable for conversational AI applications | Developing a chatbot to answer patient queries about their medical records |
| **ClassificationPipeline** [TODO] | `Tabular` | `CdsFhirConnector` | A pipeline for machine learning classification tasks | Predicting patient readmission risk based on historical health data |

Prebuilt pipelines are end-to-end workflows with Connectors built into them. They interact with raw data received from EHR interfaces, usually CDA or FHIR data from specific [protocols](../gateway/gateway.md).

You can load your models directly as a pipeline object, from local files or from a remote model repository such as Hugging Face.

```python
from healthchain.pipeline import Pipeline
from healthchain.models import CdaRequest

# Load from Hugging Face
pipeline = MedicalCodingPipeline.from_model_id(
    'gpt2', source="huggingface"
)
# Load from local model files
pipeline = MedicalCodingPipeline.from_local_model(
    '/path/to/model', source="spacy"
)
# Load from a pipeline object
pipeline = MedicalCodingPipeline.load(pipeline_object)

cda_request = CdaRequest(document="<Clinical Document>")
cda_response = pipeline(cda_request)
```

### Customizing Prebuilt Pipelines

To customize a prebuilt pipeline, you can use the [pipeline management methods](#pipeline-management) to add, remove, and replace components. For example, you may want to change the model being used. [TODO]

If you need more control and don't mind writing more code, you can subclass `BasePipeline` and implement your own pipeline logic.

[(BasePipeline API Reference)](../../api/pipeline.md#healthchain.pipeline.base.BasePipeline)

## Integrations

HealthChain offers powerful integrations with popular NLP libraries, enhancing its capabilities and allowing you to build more sophisticated pipelines. These integrations include components for spaCy, Hugging Face Transformers, and LangChain, enabling you to leverage state-of-the-art NLP models and techniques within your HealthChain workflows.

Integrations are covered in detail on the [Integrations](./integrations/integrations.md) homepage.

## Freestyle 🕺

To build your own pipeline, you can start with an empty pipeline and add components to it. Initialize your pipeline with the appropriate container type, such as `Document` or `Tabular`. This is not essential, but it allows the pipeline to enforce type safety (If you don't specify the container type, it will be inferred from the first component added.)

You can see the full list of available containers at the [Container](./data_container.md) page.

```python
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document

pipeline = Pipeline[Document]()

# Or if you live dangerously
# pipeline = Pipeline()
```

To use a built pipeline, compile it by running `.build()`. This will return a compiled pipeline that you can run on your data.

```python
pipe = pipeline.build()
doc = pipe(Document("Patient is diagnosed with diabetes"))

print(doc.entities)
```

### Adding Nodes

There are three types of nodes you can add to your pipeline with the method `.add_node()`:

- Inline Functions
- Components
- Custom Components

#### Inline Functions

Inline functions are simple functions that take in a container and return a container.

```python
@pipeline.add_node
def remove_stopwords(doc: Document) -> Document:
    stopwords = {"the", "a", "an", "in", "on", "at"}
    doc.tokens = [token for token in doc.tokens if token not in stopwords]
    return doc

# Equivalent to:
pipeline.add_node(remove_stopwords)
```

#### Components

Components are pre-configured building blocks that perform specific tasks. They are defined as separate classes and can be reused across multiple pipelines.

You can see the full list of available components at the [Components](./components/components.md) page.

```python
from healthchain.pipeline import TextPreProcessor

preprocessor = TextPreProcessor(tokenizer="spacy", lowercase=True)
pipeline.add_node(preprocessor)
```

#### Custom Components

Custom components are classes that implement the `BaseComponent` interface. You can use them to add custom processing logic to your pipeline.

```python
from healthchain.pipeline import BaseComponent

class RemoveStopwords(BaseComponent):
    def __init__(self, stopwords: List[str]):
        super().__init__()
        self.stopwords = stopwords

    def __call__(self, doc: Document) -> Document:
        doc.tokens = [token for token in doc.tokens if token not in self.stopwords]
        return doc

stopwords = ["the", "a", "an", "in", "on", "at"]
pipeline.add_node(RemoveStopwords(stopwords))
```

[(BaseComponent API Reference)](../../api/component.md#healthchain.pipeline.components.base.BaseComponent)

### Adding Connectors 🔗

Connectors are added to the pipeline using the `.add_input()` and `.add_output()` methods. You can learn more about connectors at the [Connectors](./connectors/connectors.md) documentation page.

```python
from healthchain.io import CdaConnector

cda_connector = CdaConnector()

pipeline.add_input(cda_connector)
pipeline.add_output(cda_connector)
```

## Pipeline Management 🔨

#### Adding

Use `.add_node()` to add a component to the pipeline. By default, the component will be added to the end of the pipeline and named as the function name provided.

You can specify the position of the component using the `position` parameter. Available positions are:

- `"first"`
- `"last"`
- `"default"`
- `"after"`
- `"before"`

When using `"after"` or `"before"`, you must also specify the `reference` parameter with the name of the node you want to add the component after or before.

You can also specify the `stage` parameter to add the component to a specific stage group of the pipeline.

```python
@pipeline.add_node(position="after", reference="tokenize", stage="preprocessing")
def remove_stopwords(doc: Document) -> Document:
    stopwords = {"the", "a", "an", "in", "on", "at"}
    doc.tokens = [token for token in doc.tokens if token not in stopwords]
    return doc
```

You can specify dependencies between components using the `dependencies` parameter. This is useful if you want to ensure that a component is run after another component.

```python
@pipeline.add_node(dependencies=["tokenize"])
def remove_stopwords(doc: Document) -> Document:
    stopwords = {"the", "a", "an", "in", "on", "at"}
    doc.tokens = [token for token in doc.tokens if token not in stopwords]
    return doc
```

#### Removing

Use `.remove()` to remove a component from the pipeline.

```python
pipeline.remove("remove_stopwords")
```

#### Replacing

Use `.replace()` to replace a component in the pipeline.

```python
def remove_names(doc: Document) -> Document:
    doc.entities = [token for token in doc.entities if token[0].isupper() and len(token) > 1]
    return doc

pipeline.replace("remove_stopwords", remove_names)
```

#### Inspecting the Pipeline

```python
print(pipeline)
print(pipeline.stages)

# ["TextPreprocessor", "Model", "TextPostProcessor"]
# preprocessing:
#   - TextPreprocessor
# ner+l:
#   - Model
# postprocessing:
#   - TextPostProcessor
```
