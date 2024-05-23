![GitHub License](https://img.shields.io/github/license/dotimplement/healthchain)

# HealthChain

Simplify prototyping and testing AI/NLP applications in a healthcare context 💫 🏥.

Building applications that integrate in healthcare systems is complex, and so is designing reliable, reactive algorithms involving text and structured data. Let's try to change that.

```bash
pip install healthchain
```
> 🚧 This is a work in progress with a limited set of functionalities and resources implemented. Things might break. 💥 We are working towards a full release soon! 👀


## Features
- [x] 🍱 Create sandbox servers and clients that comply with real EHRs API and data standards.
- [x] 🗃️ Generate synthetic FHIR resources or load your own data as free-text.
- [x] 💾 Save generated request and response data for each sandbox run.
- [x] 🎈 Streamlit dashboard to inspect generated data and responses.
- [x] 🧪 Experiment with LLMs in a fully HL7 standard-compliant pipeline from day 1.

## Clinical Decision Support (CDS)
[CDS Hooks](https://cds-hooks.org/) is an [HL7](https://cds-hooks.hl7.org) published specification for clinical decision support.

**When is this used?** CDS hooks are triggered at certain events during a clinician's workflow in an electronic health record (EHR), e.g. when a patient record is opened, when an order is elected.

**What information is sent**: the context of the event and FHIR resources that are requested by your service, for example, the patient ID and information on the encounter and conditions they are being seen for.

**What information is returned**: “cards” displaying text, actionable suggestions, or links to launch a [SMART](https://smarthealthit.org/) app from within the workflow.

**What you need to decide**: What data do I want my EHR client to send, and how will my service process this data.


```python
import healthchain as hc

from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.data_generator import DataGenerator

# Decorate class with sandbox and pass in use case
@hc.sandbox
class myCDS(ClinicalDecisionSupport):
    def __init__(self) -> None:
        self.data_generator = DataGenerator()

    # Sets up an instance of a mock EHR client of the specified workflow
    @hc.ehr(workflow="patient-view")
    def load_data(self):
        self.data_generator.generate()
        return self.data_generator.data

    # Define your application logic here
    @hc.api
    def service(self, request: str):
        result = "Hello " + request["patient_name"]
        return result

if __name__ == "__main__":
    cds = myCDS()
    cds.start_sandbox()
```

Then run:
```bash
healthchain mycds.py
```
This will populate your EHR client with the data generation method you have defined, send requests to your server for processing, and save the data in `./output' by default.

### Streamlit dashboard
Note this is currently not meant to be a frontend to the EHR client, so you will have to run it separately from the sandbox application.

```bash
streamlit streamlit-demo/app.py
```

## Road Map
- [ ] 📝 Adding Clinical Documentation use case: CDA data generation, NoteReader API, and structured data extraction applications
- [ ] 🎛️ Ability to test different EHR backend data configurations in client
- [ ] 📦 Versioning of configurations and model artifacts
- [ ] ✨ Improvements to synthetic data generator methods
- [ ] 👾 Add proper frontend for EHR client which renders more complex cards
- [ ] 🐳 Serve with Docker containers
- [ ] 🚀 Use LLMs to parse configuration and modify integration code

## Contribute
We are always eager to hear feedback and suggestions, especially if you are a developer or researcher working with healthcare systems!
- 💡 Let's chat! [Discord](https://discord.gg/jG4UWCUh)
- 🛠️ [Contribution Guidelines](CONTRIBUTING.md)

## Acknowledgement
This repository makes use of CDS Hooks developed by Boston Children’s Hospital.
