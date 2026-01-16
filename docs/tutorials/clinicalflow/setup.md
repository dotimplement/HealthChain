# Setup

Get your development environment ready for building the ClinicalFlow service.

## Install HealthChain

Create a new project directory and install HealthChain:

```bash
mkdir clinicalflow
cd clinicalflow
pip install healthchain
```

For NLP capabilities, install with the optional spaCy integration:

```bash
pip install healthchain[nlp]
```

## Verify Installation

Create a file called `check_install.py`:

```python
import healthchain
from healthchain.io import Document

print(f"HealthChain version: {healthchain.__version__}")

# Test creating a simple document
doc = Document("Patient has a history of hypertension.")
print(f"Created document with {len(doc.text)} characters")
```

Run it:

```bash
python check_install.py
```

You should see output like:

```
HealthChain version: 0.x.x
Created document with 40 characters
```

## Project Structure

Create the following project structure:

```
clinicalflow/
├── app.py              # Main CDS Hooks service
├── pipeline.py         # NLP processing pipeline
└── test_service.py     # Testing script
```

## Download Sample Data (Optional)

For testing, you can use Synthea-generated patient data. HealthChain's sandbox can load this automatically, but if you want local data:

```bash
mkdir data
# Download a sample Synthea bundle (optional)
# We'll use HealthChain's built-in data loaders in the testing step
```

## What's Next

Now that your environment is set up, let's learn about [FHIR basics](fhir-basics.md) - the healthcare data format you'll be working with.
