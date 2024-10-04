# Service

A service is typically an API of a third-party system that returns data to the client, the healthcare provider object. This is where you define your application logic.

When you decorate a function with `@hc.api` in a sandbox, the function is mounted standardized API endpoint an EHR client can make requests to. This can be defined by healthcare interoperability standards, such as HL7, or the EHR provider. HealthChain will start a [FastAPI](https://fastapi.tiangolo.com/) server with these APIs pre-defined for you.

Your service function must accept and return models appropriate for your use case. Typically the service function should accept a `Request` model and return a use case specific model, such as a list of `Card` for CDS. [This will be updated in the future]

We recommend you initialize your pipeline in the class `__init__` method.

Here are minimal examples for each use case:

=== "Clinical Documentation"
    ```python
    import healthchain as hc

    from healthchain.use_cases import ClinicalDocumentation
    from healthchain.pipeline import MedicalCodingPipeline
    from healthchain.models import CcdData

    @hc.sandbox
    class MyCoolSandbox(ClinicalDocumentation):
        def __init__(self) -> None:
            # Load your pipeline
            self.pipeline = MedicalCodingPipeline.load("./path/to/model")

        @hc.ehr(workflow="sign-note-inpatient")
        def load_data_in_client(self) -> CcdData:
            # Load your data
            with open('/path/to/data.xml', "r") as file:
                xml_string = file.read()

            return CcdData(cda_xml=xml_string)

        @hc.api
        def my_service(self, ccd_data: CcdData) -> CcdData:
            # Run your pipeline
            results = self.pipeline(ccd_data)
            return results
    ```

=== "CDS"
    ```python
    import healthchain as hc

    from healthchain.use_cases import ClinicalDecisionSupport
    from healthchain.pipeline import Pipeline
    from healthchain.models import Card, CDSRequest, CdsFhirData
    from typing import List

    @hc.sandbox
    class MyCoolSandbox(ClinicalDecisionSupport):
        def __init__(self):
            self.pipeline = Pipeline.load("./path/to/pipeline")

        @hc.ehr(workflow="patient-view")
        def load_data_in_client(self) -> CdsFhirData:
            with open('/path/to/data.json', "r") as file:
                fhir_json = file.read()

            return CdsFhirData(**fhir_json)

        @hc.api
        def my_service(self, request: CDSRequest) -> List[Card]:
            result = self.pipeline(str(request.prefetch))
            return [
                Card(
                    summary="Patient summary",
                    indicator="info",
                    source={"label": "openai"},
                    detail=result,
                )
            ]
    ```
