# Data Container

The `healthchain.io.containers` module provides classes for storing and manipulating data throughout the pipeline. The main classes are `DataContainer`, `Document`, and `Tabular`.

## DataContainer

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

## Document

The `Document` class is used to store and manipulate text data along with various annotations. It extends `BaseDocument` and provides comprehensive functionality for working with text, NLP annotations, clinical concepts, and more.

```python
from healthchain.io.containers import Document

# Create a basic document
doc = Document("Patient presents with hypertension and diabetes.")

# Access NLP annotations
print(f"Word count: {doc.word_count()}")
print(f"Tokens: {doc.nlp.get_tokens()}")
print(f"Entities: {doc.nlp.get_entities()}")

# Add clinical concepts
from healthchain.models.data.concept import ProblemConcept, MedicationConcept
doc.add_concepts(
    problems=[ProblemConcept(display_name="Hypertension")],
    medications=[MedicationConcept(display_name="Aspirin")]
)

# Generate CCD data
ccd_data = doc.generate_ccd()

# Add CDS cards and actions
from healthchain.models.responses import Card, Action
doc.add_cds_cards([Card(summary="Recommended follow-up")])
doc.add_cds_actions([Action(type="order", description="Schedule follow-up")])

# Access model outputs
huggingface_output = doc.models.get_output("huggingface", "classification")
generated_text = doc.models.get_generated_text("langchain", "summarization")

# Access spacy doc
spacy_doc = doc.nlp.get_spacy_doc()

# Iterate over tokens
for token in doc:
    print(token)

# Get document length (character count)
print(f"Document length: {len(doc)}")
```

The Document class includes several key components:

- `nlp`: NLP annotations (tokens, entities, embeddings, spaCy docs)
- `concepts`: Clinical concepts (problems, medications, allergies)
- `hl7`: Structured clinical documents (CCD, FHIR)
- `cds`: Clinical decision support results (cards, actions)
- `models`: ML model outputs (Hugging Face, LangChain)

Document API Reference: [healthchain.io.containers.document](../../api/containers.md#healthchain.io.containers.document)

## Tabular

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
