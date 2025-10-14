# Pipeline

HealthChain pipelines enable FHIR-native workflows that integrate directly with EHR systems. Pipelines handle the complexities of healthcare data standards like [CDA (Clinical Document Architecture)](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) and [FHIR (Fast Healthcare Interoperability Resources)](https://build.fhir.org/), allowing you to focus on building AI models while maintaining production-ready interoperability.

You can either use prebuilt pipelines optimized for common clinical workflows, or build custom pipelines from scratch for specialized use cases.

## Prebuilt 📦

HealthChain comes with a set of prebuilt pipelines that are out-of-the-box implementations of common healthcare data processing tasks:

| Pipeline | Container | Use Case | Description | Example Application |
|----------|-----------|----------|-------------|---------------------|
| [**MedicalCodingPipeline**](./prebuilt_pipelines/medicalcoding.md) | `Document` | Clinical Documentation | Processes clinical notes into FHIR Condition resources with standard medical codes | Automated ICD-10/SNOMED CT coding for billing and CDI workflows |
| [**SummarizationPipeline**](./prebuilt_pipelines/summarization.md) | `Document` | Clinical Decision Support | Generates clinical summaries as CDS Hooks cards for EHR integration | Real-time discharge summaries in Epic or Cerner workflows |
<!-- | **QAPipeline** [TODO] | `Document` | Conversational AI | A Question Answering pipeline suitable for conversational AI applications | Developing a chatbot to answer patient queries about their medical records |
| **ClassificationPipeline** [TODO] | `Tabular` | Predictive Analytics | A pipeline for machine learning classification tasks | Predicting patient readmission risk based on historical health data | -->

Prebuilt pipelines are production-ready workflows that automatically handle FHIR conversion, validation, and formatting. They integrate seamlessly with EHR systems through [adapters](./adapters/adapters.md) and [gateways](../gateway/gateway.md), supporting standards like CDS Hooks and FHIR REST APIs.

Load your models from Hugging Face, local files, or pipeline objects:

```python
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest

# Load from Hugging Face
pipeline = MedicalCodingPipeline.from_model_id(
    'blaze999/Medical-NER', task="token-classification", source="huggingface"
)
# Load from local model files
pipeline = MedicalCodingPipeline.from_local_model(
    '/path/to/model', source="spacy"
)
# Load from a pipeline object
pipeline = MedicalCodingPipeline.load(pipeline_object)

# Simple end-to-end processing
cda_request = CdaRequest(document="<Clinical Document>")
cda_response = pipeline.process_request(cda_request)

# Or manual adapter control for more granular control
from healthchain.io import CdaAdapter
adapter = CdaAdapter()
doc = adapter.parse(cda_request)
doc = pipeline(doc)
# Access: doc.fhir.problem_list, doc.fhir.medication_list
response = adapter.format(doc)
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

### Working with Healthcare Data Formats 🔄

Adapters convert between healthcare formats (CDA, FHIR, CDS Hooks) and HealthChain's internal Document objects, enabling clean separation between ML processing and format handling. This allows your pipeline to work with any healthcare data source while maintaining FHIR-native outputs.

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

You can learn more about adapters at the [Adapters](./adapters/adapters.md) documentation page.

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
