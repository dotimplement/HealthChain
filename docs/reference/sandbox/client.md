# Client

A client is a healthcare system object that requests information and processing from an external service. This is typically an EHR system, but we may also support other health objects in the future such as a CPOE (Computerized Physician Order Entry).

We can mark a client by using the decorator `@hc.ehr`. You must declare a particular **workflow** for the EHR client, which informs the sandbox how your data will be formatted. You can find more information on the [Use Cases](./use_cases/use_cases.md) documentation page.

Data returned from the client should be wrapped in a [Pydantic](https://docs.pydantic.dev/latest/) model depending on use case, e.g. `CdsFhirData`.

You can optionally specify the number of requests to generate with the `num` parameter.

=== "Clinical Documentation"
    ```python
    import healthchain as hc

    from healthchain.use_cases import ClinicalDocumentation
    from healthchain.models import CcdData

    @hc.sandbox
    class MyCoolSandbox(ClinicalDocumentation):
        def __init__(self) -> None:
            pass

        @hc.ehr(workflow="sign-note-inpatient", num=10)
        def load_data_in_client(self) -> CcdData:
            # Do things here to load in your data
            return CcdData(cda_xml="")
    ```

=== "CDS"
    ```python
    import healthchain as hc

    from healthchain.use_cases import ClinicalDecisionSupport
    from healthchain.models import CdsFhirData

    @hc.sandbox
    class MyCoolSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @hc.ehr(workflow="patient-view", num=10)
        def load_data_in_client(self) -> CdsFhirData:
            # Do things here to load in your data
            return CdsFhirData(context={}, prefetch={})

    ```
