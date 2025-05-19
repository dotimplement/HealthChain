# Service

A service is typically an API of a third-party system that returns data to the client, the healthcare provider object. This is where you define your application logic.

When you decorate a function with `@hc.api` in a sandbox, the function is mounted standardized API endpoint an EHR client can make requests to. This can be defined by healthcare interoperability standards, such as HL7, or the EHR provider. HealthChain will start a [FastAPI](https://fastapi.tiangolo.com/) server with these APIs pre-defined for you.

Your service function receives use case specific request data as input and returns the response data.

We recommend you initialize your pipeline in the class `__init__` method.

Here are minimal examples for each use case:

=== "Clinical Documentation"
    ```python
    import healthchain as hc

    from healthchain.sandbox.use_cases import ClinicalDocumentation
    from healthchain.pipeline import MedicalCodingPipeline
    from healthchain.models import CdaRequest, CdaResponse
    from healthchain.fhir import create_document_reference
    from fhir.resources.documentreference import DocumentReference

    @hc.sandbox
    class MyCoolSandbox(ClinicalDocumentation):
        def __init__(self):
            self.pipeline = MedicalCodingPipeline.load("./path/to/model")

        @hc.ehr(workflow="sign-note-inpatient")
        def load_data_in_client(self) -> DocumentReference:
            with open('/path/to/data.xml', "r") as file:
                xml_string = file.read()

            return create_document_reference(data=xml_string, content_type="text/xml")

        @hc.api
        def my_service(self, request: CdaRequest) -> CdaResponse:
            response = self.pipeline(request)
            return response
    ```

=== "CDS"
    ```python
    import healthchain as hc

    from healthchain.sandbox.use_cases import ClinicalDecisionSupport
    from healthchain.pipeline import SummarizationPipeline
    from healthchain.models import CDSRequest, CDSResponse, Prefetch
    from fhir.resources.patient import Patient

    @hc.sandbox
    class MyCoolSandbox(ClinicalDecisionSupport):
        def __init__(self):
            self.pipeline = SummarizationPipeline.load("model-name")

        @hc.ehr(workflow="patient-view")
        def load_data_in_client(self) -> Prefetch:
            with open('/path/to/data.json', "r") as file:
                fhir_json = file.read()

            return Prefetch(prefetch={"patient": Patient(**fhir_json)})

        @hc.api
        def my_service(self, request: CDSRequest) -> CDSResponse:
            response = self.pipeline(request)
            return response
    ```
