# Build a NoteReader Service with FHIR Integration

This tutorial shows you how to build a clinical coding service that connects legacy [CDA](https://hl7.org/cda/) systems with modern [FHIR servers](https://build.fhir.org/http.html). We'll process clinical notes, extract billing codes, and handle both old and new healthcare data formats. We'll use [Epic NoteReader](https://discovery.hgdata.com/product/epic-notereader-cdi) as the legacy system and [Medplum](https://www.medplum.com/) as the FHIR server.

Check out the full working example [here](https://github.com/dotimplement/HealthChain/tree/main/cookbook/notereader_clinical_coding_fhir.py)!

## Setup

We'll use [scispacy](https://allenai.github.io/scispacy/) for medical entity extraction in this example. Make sure to install the required dependencies:

```bash
pip install healthchain scispacy python-dotenv
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
```

To test the FHIR integration with Medplum, you'll need to set up a Medplum account and obtain client credentials. See the [FHIR Sandbox Setup Guide](./setup_fhir_sandboxes.md#medplum-sandbox) for detailed instructions.

Once you have your Medplum credentials, configure them in a `.env` file:

```bash
# .env file
MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
MEDPLUM_CLIENT_ID=your_client_id
MEDPLUM_CLIENT_SECRET=your_client_secret
MEDPLUM_TOKEN_URL=https://api.medplum.com/oauth2/token
MEDPLUM_SCOPE=openid
```

## Initialize the Pipeline

First, we'll build a [medical coding pipeline](../reference/pipeline/pipeline.md) with a custom entity linking node that maps extracted entities (e.g., "chronic kidney disease") to standard codes (e.g., SNOMED CT). For this demo, we'll use a simple dictionary for SNOMED CT mapping.

```python
from healthchain.pipeline.medicalcodingpipeline import MedicalCodingPipeline
from healthchain.io import Document
from spacy.tokens import Span

# Build FHIR-native ML pipeline with automatic problem extraction.
pipeline = MedicalCodingPipeline.from_model_id("en_core_sci_sm", source="spacy")

# Add custom entity linking
@pipeline.add_node(position="after", reference="SpacyNLP")
def link_entities(doc: Document) -> Document:
    """
    Add CUI codes to medical entities for problem extraction.
    """
    if not Span.has_extension("cui"):
        Span.set_extension("cui", default=None)

    spacy_doc = doc.nlp.get_spacy_doc()

    # Dummy medical concept mapping to SNOMED CT codes
    medical_concepts = {
        "pneumonia": "233604007",
        "type 2 diabetes mellitus": "44054006",
        "congestive heart failure": "42343007",
        "chronic kidney disease": "431855005",
        "hypertension": "38341003",
        # Add more mappings as needed
    }

    for ent in spacy_doc.ents:
        if ent.text.lower() in medical_concepts:
            ent._.cui = medical_concepts[ent.text.lower()]

    return doc
```

The `MedicalCodingPipeline` automatically:

- Extracts medical entities using the `scispacy` model
- Converts entities to FHIR [Condition](https://www.hl7.org/fhir/condition.html) resources
- Automatically populates the Document's `fhir.problem_list` for downstream processing

It is equivalent to building a pipeline with the following components:

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components import SpacyNLP, FHIRProblemListExtractor
from healthchain.io import Document

pipeline = Pipeline[Document]()

pipeline.add_node(SpacyNLP.from_model_id("en_core_sci_sm"))
pipeline.add_node(FHIRProblemListExtractor())
```

## Add the CDA Adapter

The [CdaAdapter](../reference/pipeline/adapters/cdaadapter.md) parses CDA XML into a [Document](../reference/pipeline/data_container.md), extracts both clinical text and coded data (e.g., conditions), and enables round-trip conversion between CDA, FHIR, and Document formats using the [InteropEngine](../reference/interop/engine.md) for seamless legacy-to-modern data integration.


```python
from healthchain.io import CdaAdapter
from healthchain.engine import create_interop

# Create an interop engine with default configuration
interop_engine = create_interop()
cda_adapter = CdaAdapter(engine=interop_engine)

# Parse the CDA document to a Document object
doc = cda_adapter.parse(request)

# Access the FHIR resources in the Document object
doc.fhir.problem_list

# Format the Document object back to a CDA document
response = cda_adapter.format(doc)
```

!!! info "What this adapter does"

    - Parses CDA XML documents and extracts clinical text and coded data
    - Stores text data in `doc.text`
    - Stores CDA XML as a [DocumentReference](https://www.hl7.org/fhir/documentreference.html) resource in `doc.fhir.bundle`
    - Stores extracted [Condition](https://www.hl7.org/fhir/condition.html) resources in `doc.fhir.problem_list`

## Set up FHIR Gateway

[FHIR gateways](../reference/gateway/fhir_gateway.md) enable your app to connect to one or more external FHIR servers (like EHRs, registries, billing systems). Use `add_source` to register each FHIR endpoint with its connection string; the gateway manages authentication, routing, and merging data across sources, allowing unified access to patient data.

```python
from healthchain.gateway import FHIRGateway
from healthchain.gateway.clients.fhir.base import FHIRAuthConfig
from dotenv import load_dotenv

load_dotenv()

# Load configuration from environment variables
config = FHIRAuthConfig.from_env("MEDPLUM")
BILLING_URL = config.to_connection_string()

# Initialize FHIR gateway and register external systems
fhir_gateway = FHIRGateway()
fhir_gateway.add_source("billing", BILLING_URL)

# You can add multiple FHIR sources:
# fhir_gateway.add_source("ehr", "fhir://epic.example.com/fhir/R4/")
# fhir_gateway.add_source("registry", "fhir://registry.example.com/fhir/R4/")
```

## Set Up the NoteReader Service

Now let's set up the handler for [NoteReader Service](../reference/gateway/soap_cda.md).

!!! note "About NoteReader"

    Epic NoteReader is a legacy SOAP/CDA interface for clinical documentation improvement (CDI) workflows. While it's rigid and dated, it's already integrated into existing EHR workflows. We can modernize it by routing extracted conditions to FHIR servers for additional processing.

```python
from healthchain.gateway import NoteReaderService

# Create the NoteReader service
note_service = NoteReaderService()

@note_service.method("ProcessDocument")
def ai_coding_workflow(request: CdaRequest):
    # Parse CDA document from legacy system
    doc = cda_adapter.parse(request)

    # Process through ML pipeline to extract medical entities
    doc = pipeline(doc)

    # Access the extracted FHIR resources
    for condition in doc.fhir.problem_list:
        # Add metadata for audit and provenance tracking
        condition = add_provenance_metadata(
            condition, source="epic-notereader", tag_code="cdi"
        )
        # Send to external FHIR server via gateway
        fhir_gateway.create(condition, source="billing")

    # Return processed CDA response to the legacy system
    cda_response = cda_adapter.format(doc)

    return cda_response
```

## Build the Service

Time to put it all together! Using [HealthChainAPI](../reference/gateway/api.md), we can create a service with both FHIR and NoteReader endpoints.

```python
from healthchain.gateway import HealthChainAPI

# Register services with the API gateway
app = HealthChainAPI(title="Healthcare Integration Gateway")

app.register_gateway(fhir_gateway, path="/fhir")
app.register_service(note_service, path="/notereader")
```

## Test with Sample Documents

Use the [sandbox utility](../reference/utilities/sandbox.md) to test with sample clinical documents:

!!! note "Download Sample Data"

    Download sample CDA files from [cookbook/data](https://github.com/dotimplement/HealthChain/tree/main/cookbook/data) and place them in a `data/` folder in your project root.

```python
import healthchain as hc

from healthchain.sandbox.use_cases import ClinicalDocumentation
from healthchain.fhir import create_document_reference

from fhir.resources.documentreference import DocumentReference

def create_sandbox():
    @hc.sandbox(api="http://localhost:8000/")
    class NotereaderSandbox(ClinicalDocumentation):
        """Sandbox for testing clinical documentation workflows"""
        def __init__(self):
            super().__init__()
            self.data_path = "./data/notereader_cda.xml"

        @hc.ehr(workflow="sign-note-inpatient")
        def load_clinical_document(self) -> DocumentReference:
            """Load a sample CDA document for processing"""
            with open(self.data_path, "r") as file:
                xml_content = file.read()

            return create_document_reference(
                data=xml_content,
                content_type="text/xml",
                description="Sample CDA document from sandbox",
            )

    return NotereaderSandbox()
```

## Run the Complete Example

Run `HealthChainAPI` with `uvicorn` and start the sandbox to test the service.

```python
import uvicorn

uvicorn.run(app)

sandbox = create_sandbox()
sandbox.start_sandbox()
```

## What You've Built

A clinical coding service that bridges legacy CDA systems with modern FHIR infrastructure:

- **Legacy system integration** - Processes CDA documents from Epic NoteReader workflows
- **AI-powered extraction** - Uses NLP to extract medical entities and map to SNOMED CT codes
- **FHIR interoperability** - Converts extracted conditions to FHIR resources and syncs with external servers
- **Audit trail** - Tracks provenance metadata for compliance and debugging
- **Dual interface** - Maintains CDA compatibility while enabling modern FHIR operations

!!! info "Use Cases"

    - **Clinical Documentation Improvement (CDI)**
      Automatically extract billable conditions from clinical notes and populate problem lists in real-time during clinician workflows.

    - **Terminology Harmonization**
      Bridge legacy ICD-9 systems with modern SNOMED CT standards by processing historical CDA documents and creating FHIR-compliant problem lists.

    - **Research Data Extraction**
      Extract structured condition data from unstructured clinical notes for cohort building and retrospective studies.

!!! tip "Next Steps"

    - **Enhance entity linking**: Replace the dictionary lookup with terminology servers or entity linking models for comprehensive medical terminology coverage.
    - **Add validation**: Implement FHIR resource validation before sending to external servers.
    - **Expand to other workflows**: Adapt the pattern for lab results, medications, or radiology reports.
    - **Build on it**: Use the extracted conditions in the [Data Aggregation tutorial](./data_aggregation.md) to combine with other FHIR sources.
