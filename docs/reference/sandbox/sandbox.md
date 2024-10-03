# Sandbox

Designing your pipeline to integrate well in a healthcare context is an essential step to turning it into an application that
could potentially be adapted for real-world use. As a developer who has years of experience deploying healthcare NLP solutions into hospitals, I know how painful and slow this process can be in reality.

A sandbox makes this process easier. It provides a staging environment to debug, test, track, and interact with your application in realistic deployment scenarios without having to gain access to such environments, especially ones that are tightly integrated with local EHR configurations. Think of it as integration testing in healthcare systems.

For a given sandbox run:

1. Data is generated or loaded into a client (EHR)

2. Data is wrapped and sent as standardized API requests the designated service

3. Data is processed by the service (you application)

4. Processed result is wrapped and sent back to the service as a standardized API response

5. Data is received by the client which could be rendered in a UI interface

To create a sandbox, initialize a class that inherits from a type of `UseCase` and decorate it with the `@hc.sandbox` decorator. `UseCase` loads in the blueprint of the API endpoints for the specified use case, and `@hc.sandbox` orchestrates these interactions.

Every sandbox also requires a **client** function marked by `@hc.ehr` and a **service** function marked by `@hc.api`. Every client function must specify a **workflow** that informs the sandbox how your data will be formatted. For more information on workflows, see the [Use Cases](./use_cases/use_cases.md) documentation.

!!! success "For each sandbox you need to specify..."

    - Use case
    - service function
    - client function
    - workflow of client

```bash
pip install torch transformers
```

```python
import healthchain as hc

from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.data_generators import CdsDataGenerator
from healthchain.models import Card, CDSRequest, CdsFhirData
from transformers import pipeline

from typing import List

@hc.sandbox
class MyCoolSandbox(ClinicalDecisionSupport):
    def __init__(self):
        self.data_generator = CdsDataGenerator()
        self.pipeline = pipeline('summarization')

    @hc.ehr(workflow="patient-view")
    def load_data_in_client(self) -> CdsFhirData:
        with open('/path/to/data.json', "r") as file:
            fhir_json = file.read()

        return CdsFhirData(**fhir_json)

    @hc.api
    def my_service(self, request: CDSRequest) -> List[Card]:
        results = self.pipeline(str(request.prefetch))
        return [
            Card(
                summary="Patient summary",
                indicator="info",
                source={"label": "transformers"},
                detail=results[0]['summary_text'],
            )
        ]

if __name__ == "__main__":
    cds = MyCoolSandbox()
    cds.start_sandbox()
```
