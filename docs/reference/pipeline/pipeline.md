# Pipeline

HealthChain pipelines help you quickly build data processing workflows that integrate seamlessly with EHR systems. They support healthcare formats like [FHIR](https://build.fhir.org/) out of the box and include built-in NLP to process free-text and structured clinical data—so you can focus on AI, not integration hassles.

Choose from prebuilt pipelines tailored to standard clinical workflows, or build custom pipelines for your own applications. Both approaches ensure production-ready interoperability and make it easy to adapt pipelines for any healthcare use case.

## Prebuilt 📦

HealthChain comes with a set of end-to-end pipeline implementations of common healthcare data processing tasks.

These prebuilt pipelines handle FHIR conversion, validation, and EHR integration for you. They work out-of-the-box with [**Adapters**](../io/adapters/adapters.md) and [**Gateways**](../gateway/gateway.md), supporting CDS Hooks, NoteReader CDI, and FHIR APIs. They're great for a quick setup to build more complex integrations on top of.


| Pipeline | Container | Use Case | Description | Example Application |
|----------|-----------|----------|-------------|---------------------|
| [**MedicalCodingPipeline**](./prebuilt_pipelines/medicalcoding.md) | `Document` | Clinical Documentation | Processes clinical notes into FHIR Condition resources with standard medical codes | Automated ICD-10/SNOMED CT coding for billing and CDI workflows |
| [**SummarizationPipeline**](./prebuilt_pipelines/summarization.md) | `Document` | Clinical Decision Support | Generates clinical summaries as CDS Hooks cards for EHR integration | Real-time discharge summaries in Epic or Cerner workflows |
<!-- | **QAPipeline** [TODO] | `Document` | Conversational AI | A Question Answering pipeline suitable for conversational AI applications | Developing a chatbot to answer patient queries about their medical records |
| **ClassificationPipeline** [TODO] | `Tabular` | Predictive Analytics | A pipeline for machine learning classification tasks | Predicting patient readmission risk based on historical health data | -->

When you load your data into a prebuilt pipeline, it receives and returns request and response data ready to send to EHR integration points:

```python
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest

# Load from a pipeline object
pipeline = MedicalCodingPipeline.load(pipeline_object)

# Simple end-to-end processing
cda_request = CdaRequest(document="<Clinical Document>")
cda_response = pipeline.process_request(cda_request)
```

### Customizing Prebuilt Pipelines

To customize a prebuilt pipeline, you can use the [pipeline management](#pipeline-management) methods to add, remove, and replace components.

If you need more control and don't mind writing more code, you can subclass `BasePipeline` and implement your own pipeline logic.

[(BasePipeline API Reference)](../../api/pipeline.md#healthchain.pipeline.base.BasePipeline)

## NLP Integrations

HealthChain integrates directly with popular NLP libraries like spaCy, HuggingFace Transformers, and LangChain. Easily add advanced NLP models and components into your pipelines to power state-of-the-art healthcare AI workflows.

[(Full Documentation on NLP Integrations)](./integrations/integrations.md)

```python
from healthchain.pipeline import MedicalCodingPipeline

# Load from Hugging Face
pipeline = MedicalCodingPipeline.from_model_id(
    'blaze999/Medical-NER', task="token-classification", source="huggingface"
)
# Load from local model files
pipeline = MedicalCodingPipeline.from_local_model(
    '/path/to/model', source="spacy"
)
```

## Freestyle 🕺

[**Containers**](../io/containers/containers.md) are at the core of HealthChain pipelines: they define your data type and flow through each pipeline step, just like spaCy's `Doc`.

Specify the container (e.g. [Document](../io/containers/document.md) or [Dataset](../io/containers/dataset.md)) when creating your pipeline (`Pipeline[Document]()`). Each node processes and returns the container, enabling smooth, type-safe, modular workflows and direct FHIR conversion.

```python
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document

pipeline = Pipeline[Document]()
```

To use a built pipeline, compile it by running `.build()`. This will return a compiled pipeline that you can run on your data.

```python
# Compile the pipeline to create a callable object
pipe = pipeline.build()

# Create a Document with your clinical text and run it through the pipeline
doc = pipe(Document("Patient is diagnosed with diabetes"))

# Print the extracted problem list items
print(doc.fhir.problem_list)
```

### Adding Nodes

There are three types of nodes you can add to your pipeline with the method `.add_node()`:

- Inline Functions
- Components
- Custom Components

#### Inline Functions

Inline functions are simple functions that process Document containers. Use them for custom clinical logic without creating full components.

```python
from spacy.tokens import Span

@pipeline.add_node
def link_snomed_codes(doc: Document) -> Document:
    """Map medical entities to SNOMED CT codes."""
    if not Span.has_extension("cui"):
        Span.set_extension("cui", default=None)

    spacy_doc = doc.nlp.get_spacy_doc()

    # Map clinical terms to SNOMED CT
    snomed_mapping = {
        "hypertension": "38341003",
        "diabetes": "73211009",
        "pneumonia": "233604007",
    }

    for ent in spacy_doc.ents:
        if ent.text.lower() in snomed_mapping:
            ent._.cui = snomed_mapping[ent.text.lower()]

    return doc

# Equivalent to:
pipeline.add_node(link_snomed_codes)
```

#### Components

Components are pre-configured building blocks for common clinical NLP tasks. They handle FHIR conversion, entity extraction, and CDS formatting automatically.

See the full list at the [Components](./components/components.md) page.

```python
from healthchain.pipeline.components import SpacyNLP, FHIRProblemListExtractor

# Add medical NLP processing
nlp = SpacyNLP.from_model_id("en_core_sci_sm")
pipeline.add_node(nlp)

# Extract FHIR Condition resources from entities
extractor = FHIRProblemListExtractor()
pipeline.add_node(extractor)
```

#### Custom Components

Custom components implement the `BaseComponent` interface for reusable clinical processing logic.

```python
from healthchain.pipeline import BaseComponent
from healthchain.fhir import create_condition

class ClinicalEntityLinker(BaseComponent):
    """Links extracted entities to standard medical terminologies."""

    def __init__(self, terminology_service_url: str):
        super().__init__()
        self.terminology_url = terminology_service_url

    def __call__(self, doc: Document) -> Document:
        """Convert medical entities to FHIR Conditions."""
        spacy_doc = doc.nlp.get_spacy_doc()

        for ent in spacy_doc.ents:
            if ent._.cui:  # Has SNOMED CT code
                condition = create_condition(
                    subject=f"Patient/{doc.patient_id}",
                    code=ent._.cui,
                    display=ent.text
                )
                doc.fhir.problem_list.append(condition)

        return doc

# Add to pipeline
linker = ClinicalEntityLinker(terminology_service_url="https://terminology.hl7.org/")
pipeline.add_node(linker)
```

[(BaseComponent API Reference)](../../api/component.md#healthchain.pipeline.components.base.BaseComponent)


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
@pipeline.add_node(position="after", reference="SpacyNLP", stage="entity_linking")
def link_snomed_codes(doc: Document) -> Document:
    """Add SNOMED CT codes to extracted medical entities."""
    spacy_doc = doc.nlp.get_spacy_doc()
    snomed_mapping = {
        "hypertension": "38341003",
        "diabetes": "73211009",
    }
    for ent in spacy_doc.ents:
        if ent.text.lower() in snomed_mapping:
            ent._.cui = snomed_mapping[ent.text.lower()]
    return doc
```

You can specify dependencies between components using the `dependencies` parameter. This is useful if you want to ensure that a component is run after another component.

```python
@pipeline.add_node(dependencies=["SpacyNLP"])
def extract_medications(doc: Document) -> Document:
    """Extract medication entities and convert to FHIR MedicationStatements."""
    spacy_doc = doc.nlp.get_spacy_doc()

    for ent in spacy_doc.ents:
        if ent.label_ == "MEDICATION":
            # Create FHIR MedicationStatement
            med_statement = create_medication_statement(
                subject=f"Patient/{doc.patient_id}",
                code=ent._.cui if hasattr(ent._, "cui") else None,
                display=ent.text
            )
            doc.fhir.medication_list.append(med_statement)

    return doc
```

#### Removing

Use `.remove()` to remove a component from the pipeline.

```python
pipeline.remove("link_snomed_codes")
```

#### Replacing

Use `.replace()` to replace a component in the pipeline.

```python
def enhanced_entity_linking(doc: Document) -> Document:
    """Enhanced entity linking with external terminology service."""
    spacy_doc = doc.nlp.get_spacy_doc()

    for ent in spacy_doc.ents:
        # Call external terminology service for validation
        validated_code = terminology_service.validate(ent.text)
        if validated_code:
            ent._.cui = validated_code

    return doc

# Replace basic linking with enhanced version
pipeline.replace("link_snomed_codes", enhanced_entity_linking)
```

#### Inspecting the Pipeline

```python
print(pipeline)
print(pipeline.stages)

# ["SpacyNLP", "ClinicalEntityLinker", "FHIRProblemListExtractor"]
# preprocessing:
#   - SpacyNLP
# entity_linking:
#   - ClinicalEntityLinker
# fhir_conversion:
#   - FHIRProblemListExtractor
```
## Working with Healthcare Data Formats 🔄

Adapters let you easily convert between healthcare formats (CDA, FHIR, CDS Hooks) and HealthChain Documents. Keep your ML pipeline format-agnostic while always getting FHIR-ready outputs.

[(Full Documentation on Adapters)](../io/adapters/adapters.md)

```python
from healthchain.io import CdaAdapter, Document

adapter = CdaAdapter()

# Parse healthcare data into Document
doc = adapter.parse(cda_request)

# Process with pure pipeline
processed_doc = pipeline(doc)

# Convert back to healthcare format
response = adapter.format(processed_doc)
```
