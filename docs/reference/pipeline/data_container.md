# Data Container

The `healthchain.io.containers` module provides classes for storing and manipulating data throughout the pipeline. The main classes are `DataContainer`, `Document`, and `Tabular`.

## DataContainer 📦

`DataContainer` is a generic base class for storing data of any type.

```python
from healthchain.io.containers import DataContainer

# Create a DataContainer with string data
container = DataContainer("Some data")

# Convert to dictionary and JSON
data_dict = container.to_dict()
data_json = container.to_json()

# Create from dictionary or JSON
container_from_dict = DataContainer.from_dict(data_dict)
container_from_json = DataContainer.from_json(data_json)
```

## Document 📄

The `Document` class provides comprehensive functionality for working with text, NLP annotations, FHIR resources, and more.

| Attribute | Access | Primary Purpose | Key Features | Common Use Cases |
|-----------|--------|----------------|--------------|------------------|
| [**FHIR Data**](#fhir-data-docfhir) | `doc.fhir` | Manage clinical data in FHIR format | • Resource bundles<br>• Clinical lists (problems, meds, allergies)<br>• Document references<br>• CDS prefetch | • Store patient records<br>• Track medical history<br>• Manage clinical documents |
| [**NLP**](#nlp-component-docnlp) | `doc.nlp` | Process and analyze text | • Tokenization<br>• Entity recognition<br>• Embeddings<br>• spaCy integration | • Extract medical terms<br>• Analyze clinical text<br>• Generate features |
| [**CDS**](#clinical-decision-support-doccds) | `doc.cds` | Clinical decision support | • Recommendation cards<br>• Suggested actions<br>• Clinical alerts | • Generate alerts<br>• Suggest interventions<br>• Guide clinical decisions |
| [**Model Outputs**](#model-outputs-docmodels) | `doc.models` | Store ML model results | • Multi-framework support<br>• Task-specific outputs<br>• Text generation | • Store classifications<br>• Keep predictions<br>• Track generations |

### FHIR Data (`doc.fhir`)

The FHIR component serves as a comprehensive manager for FHIR resources, providing:

**Storage and Management:**

   - Automatic `Bundle` creation and management
   - Resource type validation
   - Convenient access to common clinical data lists

**Clinical Data Lists:**

   - `problem_list`: List of `Condition` resources (diagnoses, problems)
   - `medication_list`: List of `MedicationStatement` resources
   - `allergy_list`: List of `AllergyIntolerance` resources

**Document Reference Management:**

   - Document relationship tracking (parent/child/sibling)
   - Attachment handling with `base64` encoding
   - Document family retrieval

**CDS Support:**

   - Support for CDS Hooks prefetch resources
   - Resource indexing by type

Example usage:

```python
from healthchain.io import Document
from healthchain.fhir import (
    create_condition,
    create_medication_statement,
    create_document_reference,
)

# Basic usage with clinical lists
doc = Document("Patient presents with hypertension")

# Add problems to the problem list
doc.fhir.problem_list = [
    create_condition(subject="Patient/123", code="38341003", display="Hypertension")
]

# Add medications
doc.fhir.medication_list = [
    create_medication_statement(
        subject="Patient/123", code="1049221", display="Acetaminophen"
    )
]

# Working with document references
parent_doc = create_document_reference(
    data="Original clinical note", content_type="text/plain"
)
parent_id = doc.fhir.add_document_reference(parent_doc)

# Add a child document with relationship
child_doc = create_document_reference(
    data="Updated clinical note", content_type="text/plain"
)
child_id = doc.fhir.add_document_reference(
    child_doc, parent_id=parent_id, relationship_type="replaces"
)

# Get document family (parents/children/siblings)
family = doc.fhir.get_document_reference_family(child_id)
print(f"Parent doc: {family['parents'][0].description}")

# Using CDS prefetch resources
prefetch = {
    "Condition": doc.fhir.problem_list,
    "MedicationStatement": doc.fhir.medication_list,
}
doc.fhir.set_prefetch_resources(prefetch)
conditions = doc.fhir.get_prefetch_resources("Condition")

```

**Technical Notes:**

- All FHIR resources are validated using [fhir.resources](https://github.com/nazrulworld/fhir.resources)
- Document relationships follow the FHIR [DocumentReference.relatesTo](https://www.hl7.org/fhir/documentreference-definitions.html#DocumentReference.relatesTo) standard

**Resource Documentation:**

- [FHIR Bundle](https://www.hl7.org/fhir/bundle.html)
- [FHIR DocumentReference](https://www.hl7.org/fhir/documentreference.html)
- [FHIR Condition](https://www.hl7.org/fhir/condition.html)
- [FHIR MedicationStatement](https://www.hl7.org/fhir/medicationstatement.html)
- [FHIR AllergyIntolerance](https://www.hl7.org/fhir/allergyintolerance.html)

### NLP Component (`doc.nlp`)

- `get_tokens()`: Returns list of tokens from the text
- `get_entities()`: Returns named entities with optional CUI (SNOMED CT concept IDs)
- `get_embeddings()`: Returns vector representations of text
- `get_spacy_doc()`: Returns the underlying spaCy document for advanced NLP features
- `word_count()`: Returns total word count based on tokenization


### Clinical Decision Support (`doc.cds`)

- `cards`: List of Card objects with clinical recommendations
- `actions`: List of Action objects for suggested interventions


### Model Outputs (`doc.models`)

- `get_output(model_name, task)`: Get specific model output
- `get_generated_text(model_name, task)`: Get generated text
- Supports outputs from various models (e.g., Hugging Face, LangChain)

Example using all components:
```python
from healthchain.io import Document
from healthchain.fhir import create_condition
from healthchain.models import Card, Action

# Create document with text
doc = Document("Patient reports chest pain and shortness of breath.")

# Access and update NLP features
print(f"Word count: {doc.word_count()}")
tokens = doc.nlp.get_tokens()
spacy_doc = doc.nlp.get_spacy_doc()

# Add FHIR resources
doc.fhir.problem_list.append(
    create_condition(subject="Patient/123", code="29857009", display="Chest pain")
)

# Update problem list from NLP entities (requires spaCy doc with CUI extension)
doc.update_problem_list_from_nlp()

# Add CDS results
doc.cds.cards = [
    Card(
        summary="Consider cardiac evaluation",
        indicator="warning",
        source={"label": "AHA Guidelines"},
    )
]
doc.cds.actions = [Action(...)]

# Get model outputs
classification = doc.models.get_output("huggingface", "classification")

```

[Document API Reference](../../api/containers.md#healthchain.io.containers.document)

## Tabular 📊

The `Tabular` class is used for storing and manipulating tabular data, wrapping a pandas DataFrame.

```python
import pandas as pd
from healthchain.io.containers import Tabular

# Create a Tabular object from a DataFrame
df = pd.DataFrame({'A': [1, 2, 3], 'B': ['a', 'b', 'c']})
tabular = Tabular(df)

# Access basic information
print(f"Columns: {tabular.columns}")
print(f"Row count: {tabular.row_count()}")
print(f"Column count: {tabular.column_count()}")
print(f"Data types: {tabular.dtypes}")

# Describe the tabular data
print(tabular.describe())

# Remove a column
tabular.remove_column('A')

# Save to CSV
tabular.to_csv('output.csv')

# Create from CSV
tabular_from_csv = Tabular.from_csv('input.csv')
```

These classes provide a consistent interface for working with different types of data in the healthchain pipeline.
