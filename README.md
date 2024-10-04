<div align="center" style="margin-bottom: 1em;">

# HealthChain 💫 🏥

<img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/healthchain_logo.png" alt="HealthChain Logo" width=300></img>

![GitHub License](https://img.shields.io/github/license/dotimplement/HealthChain)
![PyPI Version](https://img.shields.io/pypi/v/healthchain) ![Python Versions](https://img.shields.io/pypi/pyversions/healthchain)
![Downloads](https://img.shields.io/pypi/dm/healthchain)

</div>

Simplify developing, testing and validating AI and NLP applications in a healthcare context 💫 🏥.

Building applications that integrate with electronic health record systems (EHRs) is complex, and so is designing reliable, reactive algorithms involving unstructured data. Let's try to change that.

```bash
pip install healthchain
```
First time here? Check out our [Docs](https://dotimplement.github.io/HealthChain/) page!

## Features
- [x] 🛠️ Build custom pipelines or use [pre-built ones](https://dotimplement.github.io/HealthChain/reference/pipeline/pipeline/#prebuilt) for your healthcare NLP and ML tasks
- [x] 🏗️ Add built-in CDA and FHIR parsers to connect your pipeline to interoperability standards
- [x] 🧪 Test your pipelines in full healthcare-context aware [sandbox](https://dotimplement.github.io/HealthChain/reference/sandbox/sandbox/) environments
- [x] 🗃️ Generate [synthetic healthcare data](https://dotimplement.github.io/HealthChain/reference/utilities/data_generator/) for testing and development
- [x] 🚀 Deploy sandbox servers locally with [FastAPI](https://fastapi.tiangolo.com/)

## Why use HealthChain?
-  **EHR integrations are manual and time-consuming** - HealthChain abstracts away complexities so you can focus on AI development, not EHR configurations.
-  **It's difficult to track and evaluate multiple integration instances** - HealthChain provides a framework to test the real-world resilience of your whole system, not just your models.
-  [**Most healthcare data is unstructured**](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6372467/) - HealthChain is optimized for real-time AI and NLP applications that deal with realistic healthcare data.
- **Built by health tech developers, for health tech developers** - HealthChain is tech stack agnostic, modular, and easily extensible.

## Pipeline
Pipelines provide a flexible way to build and manage processing pipelines for NLP and ML tasks that can easily interface with parsers and connectors to integrate with EHRs.

### Building a pipeline

```python
from healthchain.io.containers import Document
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components import TextPreProcessor, Model, TextPostProcessor

# Initialize the pipeline
nlp_pipeline = Pipeline[Document]()

# Add TextPreProcessor component
preprocessor = TextPreProcessor(tokenizer="spacy")
nlp_pipeline.add(preprocessor)

# Add Model component (assuming we have a pre-trained model)
model = Model(model_path="path/to/pretrained/model")
nlp_pipeline.add(model)

# Add TextPostProcessor component
postprocessor = TextPostProcessor(
    postcoordination_lookup={
        "heart attack": "myocardial infarction",
        "high blood pressure": "hypertension"
    }
)
nlp_pipeline.add(postprocessor)

# Build the pipeline
nlp = nlp_pipeline.build()

# Use the pipeline
result = nlp(Document("Patient has a history of heart attack and high blood pressure."))

print(f"Entities: {result.entities}")
```
### Using pre-built pipelines

```python
from healthchain.io.containers import Document
from healthchain.pipeline import MedicalCodingPipeline

# Load the pre-built MedicalCodingPipeline
pipeline = MedicalCodingPipeline.load("./path/to/model")

# Create a document to process
result = pipeline(Document("Patient has a history of myocardial infarction and hypertension."))

print(f"Entities: {result.entities}")
```

## Sandbox

Sandboxes provide a staging environment for testing and validating your pipeline in a realistic healthcare context.

### Clinical Decision Support (CDS)
[CDS Hooks](https://cds-hooks.org/) is an [HL7](https://cds-hooks.hl7.org) published specification for clinical decision support.

**When is this used?** CDS hooks are triggered at certain events during a clinician's workflow in an electronic health record (EHR), e.g. when a patient record is opened, when an order is elected.

**What information is sent**: the context of the event and [FHIR](https://hl7.org/fhir/) resources that are requested by your service, for example, the patient ID and information on the encounter and conditions they are being seen for.

**What information is returned**: “cards” displaying text, actionable suggestions, or links to launch a [SMART](https://smarthealthit.org/) app from within the workflow.


```python
import healthchain as hc

from healthchain.pipeline import Pipeline
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.models import Card, CdsFhirData, CDSRequest
from healthchain.data_generator import CdsDataGenerator
from typing import List

@hc.sandbox
class MyCDS(ClinicalDecisionSupport):
    def __init__(self) -> None:
        self.pipeline = Pipeline.load("./path/to/model")
        self.data_generator = CdsDataGenerator()

    # Sets up an instance of a mock EHR client of the specified workflow
    @hc.ehr(workflow="patient-view")
    def ehr_database_client(self) -> CdsFhirData:
        return self.data_generator.generate()

    # Define your application logic here
    @hc.api
    def my_service(self, data: CDSRequest) -> List[Card]:
        result = self.pipeline(data)
        return [
            Card(
                summary="Welcome to our Clinical Decision Support service.",
                detail=result.summary,
                indicator="info"
            )
        ]
```

### Clinical Documentation

The `ClinicalDocumentation` use case implements a real-time Clinical Documentation Improvement (CDI) service. It helps convert free-text medical documentation into coded information that can be used for billing, quality reporting, and clinical decision support.

**When is this used?** Triggered when a clinician opts in to a CDI functionality (e.g. Epic NoteReader) and signs or pends a note after writing it.

**What information is sent**: A [CDA (Clinical Document Architecture)](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/) document which contains continuity of care data and free-text data, e.g. a patient's problem list and the progress note that the clinician has entered in the EHR.

```python
import healthchain as hc

from healthchain.pipeline import MedicalCodingPipeline
from healthchain.use_cases import ClinicalDocumentation
from healthchain.models import CcdData, ProblemConcept, Quantity,

@hc.sandbox
class NotereaderSandbox(ClinicalDocumentation):
    def __init__(self):
        self.pipeline = MedicalCodingPipeline.load("./path/to/model")

    # Load an existing CDA file
    @hc.ehr(workflow="sign-note-inpatient")
    def load_data_in_client(self) -> CcdData:
        with open("/path/to/cda/data.xml", "r") as file:
            xml_string = file.read()

        return CcdData(cda_xml=xml_string)

    @hc.api
    def my_service(self, ccd_data: CcdData) -> CcdData:
        annotated_ccd = self.pipeline(ccd_data)
        return annotated_ccd
```
### Running a sandbox

Ensure you run the following commands in your `mycds.py` file:

```python
cds = MyCDS()
cds.run_sandbox()
```
This will populate your EHR client with the data generation method you have defined, send requests to your server for processing, and save the data in the `./output` directory.

Then run:
```bash
healthchain run mycds.py
```
By default, the server runs at `http://127.0.0.1:8000`, and you can interact with the exposed endpoints at `/docs`.
## Road Map
- [ ] 🎛️ Versioning and artifact management for pipelines sandbox EHR configurations
- [ ] 🤖 Integrations with other pipeline libraries such as spaCy, HuggingFace, LangChain etc.
- [ ] ❓ Testing and evaluation framework for pipelines and use cases
- [ ] 🧠 Multi-modal pipelines that that have built-in NLP to utilize unstructured data
- [ ] ✨ Improvements to synthetic data generator methods
- [ ] 👾 Frontend UI for EHR client and visualization features
- [ ] 🚀 Production deployment options

## Contribute
We are always eager to hear feedback and suggestions, especially if you are a developer or researcher working with healthcare systems!
- 💡 Let's chat! [Discord](https://discord.gg/UQC6uAepUz)
- 🛠️ [Contribution Guidelines](CONTRIBUTING.md)

## Acknowledgement
This repository makes use of CDS Hooks developed by Boston Children’s Hospital.
