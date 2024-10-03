# Pipeline

HealthChain pipelines provide a simple interface to test, version, and connect your pipeline to common healthcare data standards, such as [CDAs (Clinical Document Architecture)](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) and [FHIR (Fast Healthcare Interoperability Resources)](https://build.fhir.org/).

Depending on your need, you can either go top down, where you use prebuilt pipelines and customize them to your needs, or bottom up, where you build your own pipeline from scratch.

## Prebuilt 📦

HealthChain comes with a set of prebuilt pipelines that are out-of-the-box implementations of common healthcare data processing tasks:

| Pipeline | Container | Compatible Connector | Description | Example Use Case |
|----------|-----------|-----------|-------------|------------------|
| [**MedicalCodingPipeline**](./prebuilt_pipelines/medicalcoding.md) | `Document` | `CdaConnector` | An NLP pipeline that processes free-text clinical notes into structured data | Automatically generating SNOMED CT codes from clinical notes |
| **SummarizationPipeline** [TODO] | `Document` | `FhirConnector` | An NLP pipeline for summarizing clinical notes | Generating discharge summaries from patient history and notes |
| **QAPipeline** [TODO] | `Document` | N/A | A Question Answering pipeline suitable for conversational AI applications | Developing a chatbot to answer patient queries about their medical records |
| **ClassificationPipeline** [TODO] | `Tabular` | `FhirConnector` | A pipeline for machine learning classification tasks | Predicting patient readmission risk based on historical health data |

To use a pipeline, compile it by running `.build()` on it. This will return a compiled pipeline that you can run on your data.

Pipeline inputs and outputs are defined by the container type.

```python
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document

pipeline = MedicalCodingPipeline.load('/path/to/model')
pipeline = pipeline.build()

doc = Document(text="Patient is diagnosed with diabetes")
doc = pipeline(doc)
```

### Customizing Prebuilt Pipelines

To customize a prebuilt pipeline, you can use the [pipeline management methods](#pipeline-management) to add, remove, and replace components. For example, you may want to change the model being used. [TODO]

If you need even more control and don't mind writing more code, you can subclass `BasePipeline` and implement your own pipeline logic.

(BasePipeline API Reference)

## Freestyle 🕺

To build your own pipeline, you can start with an empty pipeline and add components to it. Initialize your pipeline with the appropriate container type, such as `Document` or `Tabular`.

You can see the full list of available containers at the [Container](./data_container.md) page.

```python
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document

pipeline = Pipeline[Document]()
```
There are three types of nodes you can add to your pipeline:

- Inline Functions
- Components
- Custom Components

### Inline Functions

Inline functions are simple functions that take in a container and return a container. They are defined directly within the `.add()` method.

```python
@pipeline.add()
def remove_stopwords(doc: Document) -> Document:
    stopwords = {"the", "a", "an", "in", "on", "at"}
    doc.tokens = [token for token in doc.tokens if token not in stopwords]
    return doc
```

### Components

Components are pre-configured building blocks that perform specific tasks. They are defined as separate classes and can be reused across multiple pipelines.

```python
from healthchain.pipeline import TextPreProcessor

preprocessor = TextPreProcessor(tokenizer="spacy", lowercase=True)
pipeline.add(preprocessor)
```
You can see the full list of available components at the [Components](./component.md) page.

### Custom Components

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
pipeline.add(RemoveStopwords(stopwords))
```

(BaseComponent API Reference)

## Pipeline Management 🔨

#### Adding

Use `.add()` to add a component to the pipeline. By default, the component will be added to the end of the pipeline and named as the function name provided.

You can specify the position of the component using the `position` parameter. Available positions are:

- `"first"`
- `"last"`
- `"default"`
- `"after"`
- `"before"`

When using `"after"` or `"before"`, you must also specify the `reference` parameter with the name of the node you want to add the component after or before.

You can also specify the `stage` parameter to add the component to a specific stage group of the pipeline.

```python
@pipeline.add(position="after", reference="tokenize", stage="preprocessing")
def remove_stopwords(doc: Document) -> Document:
    stopwords = {"the", "a", "an", "in", "on", "at"}
    doc.tokens = [token for token in doc.tokens if token not in stopwords]
    return doc
```

You can specify dependencies between components using the `dependencies` parameter. This is useful if you want to ensure that a component is run after another component.

```python
@pipeline.add(dependencies=["tokenize"])
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
