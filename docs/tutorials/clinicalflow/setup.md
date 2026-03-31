# Setup

Get your development environment ready for building the ClinicalFlow service.

## Install HealthChain

Create a new project directory:

```bash
mkdir clinicalflow
cd clinicalflow
```

### Option 1: Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. If you don't have it installed, you can install it by following the instructions [here](https://docs.astral.sh/uv/getting-started/installation/).

Then initialize a project and install HealthChain:

```bash
uv init
uv add healthchain
```


### Option 2: Using pip with a virtual environment

If you prefer using pip, create and activate a virtual environment first:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install healthchain
```

All the code running examples in this tutorial will show both the uv and pip versions of the commands. These are typically the same up to a factor of adding `uv run` at the beginning of the command.


## Verify Installation

Create a file called `check_install.py`:

```python
import healthchain
from healthchain.io import Document

# Test creating a simple document
doc = Document("Patient has a history of hypertension.")
print(f"Created document with {len(doc.text)} characters")
```

Run it:

=== "uv"

    ```bash
    uv run python check_install.py
    ```

=== "pip"

    ```bash
    python check_install.py
    ```

You should see the following output:

```
Created document with 38 characters
```

## What's Next

Now that your environment is set up, let's learn about [FHIR basics](fhir-basics.md) - the healthcare data format you'll be working with.
