# Build Pipeline

Create an NLP pipeline to process clinical text and extract structured data.

## What is a Pipeline?

A **Pipeline** in HealthChain is a sequence of processing steps that transform input data. For clinical NLP, pipelines typically:

1. Take clinical text as input
2. Process it through NLP models
3. Extract entities (conditions, medications, etc.)
4. Output structured FHIR resources

## Create Your Pipeline

Create a file called `pipeline.py`:

```python
from healthchain.pipeline import Pipeline
from healthchain.io import Document

def create_clinical_pipeline():
    """Create a pipeline for processing clinical notes."""

    # Initialize pipeline with Document as the data container
    pipeline = Pipeline[Document]()

    # Add a simple text preprocessing component
    @pipeline.add_node
    def preprocess(doc: Document) -> Document:
        """Clean and normalize clinical text."""
        # Remove extra whitespace
        doc.text = " ".join(doc.text.split())
        return doc

    # Add a clinical entity extraction component
    @pipeline.add_node
    def extract_conditions(doc: Document) -> Document:
        """Extract condition mentions from text."""
        # Simple keyword-based extraction for this tutorial
        # In production, you'd use a trained NLP model
        condition_keywords = {
            "hypertension": ("38341003", "Hypertension"),
            "diabetes": ("73211009", "Diabetes mellitus"),
            "chest pain": ("29857009", "Chest pain"),
            "shortness of breath": ("267036007", "Dyspnea"),
        }

        text_lower = doc.text.lower()
        extracted = []

        for keyword, (code, display) in condition_keywords.items():
            if keyword in text_lower:
                extracted.append({
                    "text": keyword,
                    "code": code,
                    "display": display,
                    "system": "http://snomed.info/sct"
                })

        # Store extracted conditions in document's NLP annotations
        doc.nlp.set_entities(extracted)
        return doc

    return pipeline.build()
```

## Using the Pipeline

Create a file called `test_pipeline.py` to test your pipeline:

```python
from pipeline import create_clinical_pipeline
from healthchain.io import Document

# Create the pipeline
nlp = create_clinical_pipeline()

# Process a clinical note
doc = Document(
    "Patient is a 65-year-old male presenting with chest pain "
    "and shortness of breath. History includes hypertension "
    "and diabetes, both well-controlled on current medications."
)

# Run the pipeline
result = nlp(doc)

# Check extracted entities
print("Extracted conditions:")
for entity in result.nlp.get_entities():
    print(f"  - {entity['display']} (SNOMED: {entity['code']})")
```

Run it:

=== "uv"

    ```bash
    uv run python test_pipeline.py
    ```

=== "pip"

    ```bash
    python test_pipeline.py
    ```

Expected output:

```
Extracted conditions:
  - Hypertension (SNOMED: 38341003)
  - Diabetes mellitus (SNOMED: 73211009)
  - Chest pain (SNOMED: 29857009)
  - Dyspnea (SNOMED: 267036007)
```

## Pipeline Architecture

Your pipeline now follows this flow:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Clinical   │────>│  Preprocess │────>│  Extract    │
│  Text       │     │  Text       │     │  Conditions │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  Document   │
                                        │  + Entities │
                                        └─────────────┘
```

## What's Next

Now that you have a working pipeline, let's [create a Gateway](gateway.md) to expose it as a CDS Hooks service. Don't worry if these terms don't make sense, all will be explained on the next page!
