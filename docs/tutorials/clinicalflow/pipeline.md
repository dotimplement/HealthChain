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

## Adding SpaCy Integration (Optional)

For more sophisticated NLP, you can integrate spaCy. For **medical text**, you'll need [scispaCy](https://allenai.github.io/scispacy/) - a spaCy package with biomedical models that can recognize clinical entities.

!!! warning "Model choice matters"

    General spaCy models like `en_core_web_sm` only recognize common entities (people, organizations, locations). They won't extract medical terms like "hypertension" or "diabetes". Use scispaCy models for clinical text.

!!! warning "Python version compatibility"

    scispaCy requires **Python 3.12 or earlier**. If you're using Python 3.13+, you'll encounter build errors. Check your version with `python --version`.

!!! warning "Slow installation"

    Installing scispaCy and the associated model can be slow (5-10 minutes). This is not essential to move forward with the tutorial.

Install scispaCy and a biomedical model:

=== "uv"

    ```bash
    uv pip install scispacy
    uv pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
    ```

    !!! note
        We use `uv pip install` instead of `uv add` here because scispaCy has strict dependency requirements that can cause conflicts. Using `uv pip install` installs the package without adding it to your `pyproject.toml`.

=== "pip"

    ```bash
    pip install scispacy
    pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
    ```

??? failure "Troubleshooting: Build errors with blis"

    If you see compilation errors mentioning `blis` or `'/usr/bin/cc' failed`, try installing pre-built binaries first:

    ```bash
    uv pip install blis --only-binary :all:
    uv pip install scispacy
    uv pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
    ```

    If this still fails, you may need to install build tools (`build-essential` on Ubuntu/Debian, Xcode Command Line Tools on macOS) or use a different Python version. The keyword-based pipeline shown earlier in this tutorial works without these dependencies.

Then create a pipeline with the biomedical model:

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP
from healthchain.io import Document

# Create pipeline with scispaCy biomedical model
pipeline = Pipeline[Document]()
pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
nlp = pipeline.build()

# Process a document
doc = Document("Patient presents with hypertension and diabetes.")
result = nlp(doc)

# Access the spaCy doc for full NLP features
spacy_doc = result.nlp.get_spacy_doc()
print(f"Entities: {[(ent.text, ent.label_) for ent in spacy_doc.ents]}")

# Access tokens
tokens = result.nlp.get_tokens()
print(f"Tokens: {tokens[:5]}...")  # First 5 tokens

# Access entities as dictionaries
entities = result.nlp.get_entities()
print(f"Extracted: {entities}")
```

Expected output:

```
Entities: [('hypertension', 'DISEASE'), ('diabetes', 'DISEASE')]
Tokens: ['Patient', 'presents', 'with', 'hypertension', 'and']...
Extracted: [{'text': 'hypertension', 'label': 'DISEASE', ...}, {'text': 'diabetes', 'label': 'DISEASE', ...}]
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
