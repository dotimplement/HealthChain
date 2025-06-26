<div align="center" style="margin-bottom: 1em;">

# HealthChain 💫 🏥

<img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/healthchain_logo.png" alt="HealthChain Logo" width=300></img>

![GitHub License](https://img.shields.io/github/license/dotimplement/HealthChain)
![PyPI Version](https://img.shields.io/pypi/v/healthchain) ![Python Versions](https://img.shields.io/pypi/pyversions/healthchain)
![Downloads](https://img.shields.io/pypi/dm/healthchain)

</div>

Connect your AI models to any healthcare system with a few lines of Python 💫 🏥.

Integrating AI with electronic health records (EHRs) is complex, manual, and time-consuming. Let's try to change that.


```bash
pip install healthchain
```
First time here? Check out our [Docs](https://dotimplement.github.io/HealthChain/) page!


## Features
- [x] 🔌 **Gateway**: Connect to multiple EHR systems with [unified API](https://dotimplement.github.io/HealthChain/reference/gateway/gateway/) supporting FHIR, CDS Hooks, and SOAP/CDA protocols
- [x] 🔥 **Pipelines**: Build FHIR-native ML workflows or use [pre-built ones](https://dotimplement.github.io/HealthChain/reference/pipeline/pipeline/#prebuilt) for your healthcare NLP and AI tasks
- [x] 🔄 **InteropEngine**: Convert between FHIR, CDA, and HL7v2 with a [template-based engine](https://dotimplement.github.io/HealthChain/reference/interop/interop/)
- [x] 🔒 Type-safe healthcare data with full type hints and Pydantic validation for [FHIR resources](https://dotimplement.github.io/HealthChain/reference/utilities/fhir_helpers/)
- [x] ⚡ Event-driven architecture with real-time event handling and [audit trails](https://dotimplement.github.io/HealthChain/reference/gateway/events/) built-in
- [x] 🚀 Deploy production-ready applications with [HealthChainAPI](https://dotimplement.github.io/HealthChain/reference/gateway/api/) and FastAPI integration
- [x] 🧪 Generate [synthetic healthcare data](https://dotimplement.github.io/HealthChain/reference/utilities/data_generator/) and [sandbox testing](https://dotimplement.github.io/HealthChain/reference/sandbox/sandbox/) utilities

## Why use HealthChain?
-  **EHR integrations are manual and time-consuming** - **HealthChainAPI** abstracts away complexities so you can focus on AI development, not learning FHIR APIs, CDS Hooks, and authentication schemes.
-  **Healthcare data is fragmented and complex** - **InteropEngine** handles the conversion between FHIR, CDA, and HL7v2 so you don't have to become an expert in healthcare data standards.
-  [**Most healthcare data is unstructured**](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6372467/) - HealthChain **Pipelines** are optimized for real-time AI and NLP applications that deal with realistic healthcare data.
- **Built by health tech developers, for health tech developers** - HealthChain is tech stack agnostic, modular, and easily extensible with built-in compliance and audit features.

## HealthChainAPI

The HealthChainAPI provides a secure, asynchronous integration layer that coordinates multiple healthcare systems in a single application.

### Multi-Protocol Support

Connect to multiple healthcare data sources and protocols:

```python
from healthchain.gateway import (
    HealthChainAPI, FHIRGateway,
    CDSHooksService, NoteReaderService
)

# Create your healthcare application
app = HealthChainAPI(
    title="My Healthcare AI App",
    description="AI-powered patient care platform"
)

# FHIR for patient data from multiple EHRs
fhir = FHIRGateway()
fhir.add_source("epic", "fhir://fhir.epic.com/r4?client_id=...")
fhir.add_source("medplum", "fhir://api.medplum.com/fhir/R4/?client_id=...")

# CDS Hooks for real-time clinical decision support
cds = CDSHooksService()

@cds.hook("patient-view", id="allergy-alerts")
def check_allergies(request):
    # Your AI logic here
    return {"cards": [...]}

# SOAP for clinical document processing
notes = NoteReaderService()

@notes.method("ProcessDocument")
def process_note(request):
    # Your NLP pipeline here
    return processed_document

# Register everything
app.register_gateway(fhir)
app.register_service(cds)
app.register_service(notes)

# Your API now handles:
# /fhir/* - Patient data, observations, etc.
# /cds/* - Real-time clinical alerts
# /soap/* - Clinical document processing
```

### FHIR Operations with AI Enhancement

```python
from healthchain.gateway import FHIRGateway
from fhir.resources.patient import Patient

gateway = FHIRGateway()
gateway.add_source("epic", "fhir://fhir.epic.com/r4?...")

# Add AI transformations to FHIR data
@gateway.transform(Patient)
async def enhance_patient(id: str, source: str = None) -> Patient:
    async with gateway.modify(Patient, id, source) as patient:
        # Get lab results and process with AI
        lab_results = await gateway.search(
            Observation,
            {"patient": id, "category": "laboratory"},
            source
        )
        insights = nlp_pipeline.process(patient, lab_results)

        # Add AI summary to patient record
        patient.extension = patient.extension or []
        patient.extension.append({
            "url": "http://healthchain.org/fhir/summary",
            "valueString": insights.summary
        })
        return patient

# Automatically available at: GET /fhir/transform/Patient/123?source=epic
```

## Pipeline
Pipelines provide a flexible way to build and manage processing pipelines for NLP and ML tasks that can easily integrate with complex healthcare systems.

### Building a pipeline

```python
from healthchain.io.containers import Document
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components import (
    TextPreProcessor,
    SpacyNLP,
    TextPostProcessor,
)

# Initialize the pipeline
nlp_pipeline = Pipeline[Document]()

# Add TextPreProcessor component
preprocessor = TextPreProcessor()
nlp_pipeline.add_node(preprocessor)

# Add Model component (assuming we have a pre-trained model)
spacy_nlp = SpacyNLP.from_model_id("en_core_sci_sm")
nlp_pipeline.add_node(spacy_nlp)

# Add TextPostProcessor component
postprocessor = TextPostProcessor(
    postcoordination_lookup={
        "heart attack": "myocardial infarction",
        "high blood pressure": "hypertension",
    }
)
nlp_pipeline.add_node(postprocessor)

# Build the pipeline
nlp = nlp_pipeline.build()

# Use the pipeline
result = nlp(Document("Patient has a history of heart attack and high blood pressure."))

print(f"Entities: {result.nlp.get_entities()}")
```

#### Adding connectors
Connectors give your pipelines the ability to interface with EHRs.

```python
from healthchain.io import CdaConnector
from healthchain.models import CdaRequest

cda_connector = CdaConnector()

pipeline.add_input(cda_connector)
pipeline.add_output(cda_connector)

pipe = pipeline.build()

cda_data = CdaRequest(document="<CDA XML content>")
output = pipe(cda_data)
# output: CdsResponse model
```

### Using pre-built pipelines
Pre-built pipelines are use case specific end-to-end workflows that already have connectors and models built-in.

```python
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.models import CdaRequest

# Load from model ID
pipeline = MedicalCodingPipeline.from_model_id(
    model="blaze999/Medical-NER", task="token-classification", source="huggingface"
)

# Or load from local model
pipeline = MedicalCodingPipeline.from_local_model("./path/to/model", source="spacy")

cda_data = CdaRequest(document="<CDA XML content>")
output = pipeline(cda_data)
```

## Interoperability

The InteropEngine is a template-based system that allows you to convert between FHIR, CDA, and HL7v2.

```python
from healthchain.interop import create_engine, FormatType

engine = create_engine()

with open("tests/data/test_cda.xml", "r") as f:
    cda_data = f.read()

# Convert CDA to FHIR
fhir_resources = engine.to_fhir(cda_data, src_format=FormatType.CDA)

# Convert FHIR to CDA
cda_data = engine.from_fhir(fhir_resources, dest_format=FormatType.CDA)
```

## Sandbox

Test your AI applications in realistic healthcare contexts with [CDS Hooks](https://cds-hooks.org/) sandbox environments.

```python
import healthchain as hc
from healthchain.sandbox.use_cases import ClinicalDecisionSupport

@hc.sandbox
class MyCDS(ClinicalDecisionSupport):
    def __init__(self):
        self.pipeline = SummarizationPipeline.from_model_id("facebook/bart-large-cnn")

    @hc.ehr(workflow="encounter-discharge")
    def ehr_database_client(self):
        return self.data_generator.generate_prefetch()

cds = MyCDS()
cds.start_sandbox()

# Run with: healthchain run mycds.py
```

## Road Map
- [ ] 🔒 Built-in HIPAA compliance validation and PHI detection
- [ ] 📊 Track configurations, data provenance, and monitor model performance with MLFlow integration
- [ ] 🚀 Compliance monitoring, auditing at deployment as a sidecar service
- [ ] 🔄 HL7v2 parsing and FHIR profile conversion support
- [ ] 🧠 Multi-modal pipelines


## Contribute
We are always eager to hear feedback and suggestions, especially if you are a developer or researcher working with healthcare systems!
- 💡 Let's chat! [Discord](https://discord.gg/UQC6uAepUz)
- 🛠️ [Contribution Guidelines](CONTRIBUTING.md)


## Acknowledgements 🤗
This project builds on [fhir.resources](https://github.com/nazrulworld/fhir.resources) and [CDS Hooks](https://cds-hooks.org/) standards developed by [HL7](https://www.hl7.org/) and [Boston Children's Hospital](https://www.childrenshospital.org/).
