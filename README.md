<div align="center" style="margin-bottom: 1em;">

# HealthChain 💫 🏥

<img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/healthchain_logo.png" alt="HealthChain Logo" width=300></img>

![GitHub License](https://img.shields.io/github/license/dotimplement/HealthChain)
![PyPI Version](https://img.shields.io/pypi/v/healthchain) ![Python Versions](https://img.shields.io/pypi/pyversions/healthchain)
![Downloads](https://img.shields.io/pypi/dm/healthchain)

</div>

Simplify testing and evaluating AI and NLP applications in a healthcare context 💫 🏥.

Building applications that integrate in healthcare systems is complex, and so is designing reliable, reactive algorithms involving unstructured data. Let's try to change that.

```bash
pip install healthchain
```
First time here? Check out our [Docs](dotimplement.github.io/HealthChain/) page!

## Features
- [x] 🍱 Create sandbox servers and clients that comply with real EHRs API and data standards.
- [x] 🗃️ Generate synthetic FHIR resources or load your own data as free-text.
- [x] 💾 Save generated request and response data for each sandbox run.
- [x] 🎈 Streamlit dashboard to inspect generated data and responses.
- [x] 🧪 Experiment with LLMs in an end-to-end HL7-compliant pipeline from day 1.

## Why use HealthChain?
-  **Scaling EHR integrations is a manual and time-consuming process** - HealthChain abstracts away complexities so you can focus on AI development, not EHR configurations.
-  **Evaluating the behaviour of AI in complex systems is a difficult and labor-intensive task** - HealthChain provides a framework to test the real-world resilience of your whole system, not just your models.
-  **[Most healthcare data is unstructured](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6372467/)** - HealthChain is optimised for real-time AI/NLP applications that deal with realistic healthcare data.
- **Built by health tech developers, for health tech developers** - HealthChain is tech stack agnostic, modular, and easily extensible.

## Clinical Decision Support (CDS)
[CDS Hooks](https://cds-hooks.org/) is an [HL7](https://cds-hooks.hl7.org) published specification for clinical decision support.

**When is this used?** CDS hooks are triggered at certain events during a clinician's workflow in an electronic health record (EHR), e.g. when a patient record is opened, when an order is elected.

**What information is sent**: the context of the event and FHIR resources that are requested by your service, for example, the patient ID and information on the encounter and conditions they are being seen for.

**What information is returned**: “cards” displaying text, actionable suggestions, or links to launch a [SMART](https://smarthealthit.org/) app from within the workflow.

**What you need to decide**: What data do I want my EHR client to send, and how will my service process this data.


```python
import healthchain as hc

from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.models import Card, CdsFhirData, CDSRequest
from healthchain.data_generator import DataGenerator

from typing import List

# Decorate class with sandbox and pass in use case
@hc.sandbox
class myCDS(ClinicalDecisionSupport):
    def __init__(self) -> None:
        self.data_generator = DataGenerator()

    # Sets up an instance of a mock EHR client of the specified workflow
    @hc.ehr(workflow="patient-view")
    def ehr_database_client(self) -> CdsFhirData:
        self.data_generator.generate()
        return self.data_generator.data

    # Define your application logic here
    @hc.api
    def my_service(self, request: CdsRequest) -> List[Card]:
        result = "Hello " + request["patient_name"]
        return result

if __name__ == "__main__":
    cds = myCDS()
    cds.start_sandbox()
```

Then run:
```bash
healthchain run mycds.py
```
This will populate your EHR client with the data generation method you have defined, send requests to your server for processing, and save the data in `./output` by default.

## Clinical Documentation

The ClinicalDocumentation use case implements a real-time Clinical Documentation Improvement (CDI) service. It helps convert free-text medical documentation into coded information that can be used for billing, quality reporting, and clinical decision support.

**When is this used?** Triggered when a clinician opts in to a CDI functionality (e.g. Epic NoteReader) and signs or pends a note after writing it.

**What information is sent**: A [CDA (Clinical Document Architecture)](https://www.hl7.org/implement/standards/product_brief.cfm?product_id=7) document which contains continuity of care data and free-text data, e.g. a patient's problem list and the progress note that the clinician has entered in the EHR.

**What information is returned**: A CDA document which contains additional structured data extracted and returned by your CDI service.

```python
import healthchain as hc

from healthchain.use_cases import ClinicalDocumentation
from healthchain.models import CcdData, ProblemConcept, Quantity,

@hc.sandbox
class NotereaderSandbox(ClinicalDocumentation):
    def __init__(self):
        self.cda_path = "./resources/uclh_cda.xml"

    # Load an existing CDA file
    @hc.ehr(workflow="sign-note-inpatient")
    def load_data_in_client(self) -> CcdData:
        with open(self.cda_path, "r") as file:
            xml_string = file.read()

        return CcdData(cda_xml=xml_string)

    # Define application logic
    @hc.api
    def my_service(self, ccd_data: CcdData) -> CcdData:
        # Apply method from ccd_data.note and access existing entries from ccd.problems

        new_problem = ProblemConcept(
            code="38341003",
            code_system="2.16.840.1.113883.6.96",
            code_system_name="SNOMED CT",
            display_name="Hypertension",
            )
        ccd_data.problems.append(new_problem)
        return ccd_data
```


### Streamlit dashboard
Note this is currently not meant to be a frontend to the EHR client, so you will have to run it separately from the sandbox application.

```bash
pip install streamlit
streamlit streamlit-demo/app.py
```

## Road Map
- [x] 📝 Adding Clinical Documentation use case
- [ ] 🎛️ Version and test different EHR backend configurations
- [ ] 🤖 Integrations with popular LLM and NLP libraries
- [ ] ❓ Evaluation framework for pipelines and use cases
- [ ] ✨ Improvements to synthetic data generator methods
- [ ] 👾 Frontend demo for EHR client
- [ ] 🚀 Production deployment options

## Contribute
We are always eager to hear feedback and suggestions, especially if you are a developer or researcher working with healthcare systems!
- 💡 Let's chat! [Discord](https://discord.gg/4v6XgGBZ)
- 🛠️ [Contribution Guidelines](CONTRIBUTING.md)

## Acknowledgement
This repository makes use of CDS Hooks developed by Boston Children’s Hospital.
