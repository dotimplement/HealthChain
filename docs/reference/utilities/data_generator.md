# Data Generator

Healthcare data is interoperable, but not composable - every deployment site will have different ways of configuring data and terminology. This matters when you develop applications that need to integrate into these systems, especially when you need to reliably extract data for your model to consume.

The aim of the data generator is not to generate realistic data suitable for use cases such as patient population studies, but rather to generate data that is structurally compliant with what is expected of EHR configurations, and to be able to test and handle variations in this.

For this reason the data generator is opinionated by specific workflows and use cases.

!!! note
    We're aware we may not cover everyone's use cases, so if you have strong opinions about this, please [reach out](https://discord.gg/UQC6uAepUz)!

On the synthetic data spectrum defined by [this UK ONS methodology working paper](https://www.ons.gov.uk/methodology/methodologicalpublications/generalmethodology/onsworkingpaperseries/onsmethodologyworkingpaperseriesnumber16syntheticdatapilot#:~:text=Synthetic%20data%20at%20ONS&text=Synthetic%20data%20is%20created%20by,that%20provided%20the%20original%20data.%E2%80%9D), HealthChain generates level 1: synthetic structural data.

![Synthetic data](../../assets/images/synthetic_data_ons.png)

## CDS Data Generator

The `.generate_prefetch()` method will return a `Prefetch` model with the `prefetch` field populated with a dictionary of FHIR resources. Each key in the dictionary corresponds to a FHIR resource type, and the value is a list of FHIR resources of that type. For more information, check out the [CDS Hooks documentation](https://cds-hooks.org/specification/current/#providing-fhir-resources-to-a-cds-service).

For each workflow, a pre-configured list of FHIR resources is randomly generated and placed in the `prefetch` field of a `CDSRequest`.

Current implemented workflows:

| Workflow      | Implementation Completeness        | Generated Synthetic Resources |
| ----------- | ------------------------------------ | -----------------------------
| [patient-view](https://cds-hooks.org/hooks/patient-view/) | :material-check-all:  | `Patient`, `Encounter` (Future: `MedicationStatement`, `AllergyIntolerance`)|
| [encounter-discharge](https://cds-hooks.org/hooks/encounter-discharge/)| :material-check-all: | `Patient`, `Encounter`, `Procedure`, `MedicationRequest`, Optional `DocumentReference` |
| [order-sign](https://cds-hooks.org/hooks/order-sign/)| :material-check: Partial | Future: `MedicationRequest`, `ProcedureRequest`, `ServiceRequest` |
| [order-select](https://cds-hooks.org/hooks/order-select/) | :material-check: Partial | Future: `MedicationRequest`, `ProcedureRequest`, `ServiceRequest` |

For more information on CDS workflows, see the [CDS Use Case](../sandbox/use_cases/cds.md) documentation.

You can use the data generator within a client function or on its own.

=== "Within client"
    ```python
    import healthchain as hc
    from healthchain.sandbox.use_cases import ClinicalDecisionSupport
    from healthchain.models import Prefetch
    from healthchain.data_generators import CdsDataGenerator

    @hc.sandbox
    class MyCoolSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            self.data_generator = CdsDataGenerator()

        @hc.ehr(workflow="patient-view")
        def load_data_in_client(self) -> Prefetch:
            prefetch = self.data_generator.generate_prefetch()
            return prefetch

        @hc.api
        def my_server(self, request) -> None:
            pass
    ```


=== "On its own"
    ```python
    from healthchain.data_generators import CdsDataGenerator
    from healthchain.sandbox.workflows import Workflow

    # Initialize data generator
    data_generator = CdsDataGenerator()

    # Generate FHIR resources for use case workflow
    data_generator.set_workflow(Workflow.encounter_discharge)
    prefetch = data_generator.generate_prefetch()

    print(prefetch.model_dump())

    # {
    #    "prefetch": {
    #        "encounter":
    #            {
    #              "resourceType": ...
    #            }
    #    }
    #}
    ```

<!-- You can pass in parameters in `contraint` argument to limit the general form of the FHIR resources you get back, but this feature is experimental. Arguments supported are:
- `"has_medication_request"`
- `"has_problem_list"`
- `"has_procedures"`
- `"long_encounter_period"`

```python
data_generator.generate(constrain=["has_medication_requests"])
```
-->

## Other synthetic data sources

If you are looking for realistic datasets, you are also free to load your own data in a sandbox run! Check out [MIMIC](https://mimic.mit.edu/) for comprehensive continuity of care records and free-text data, or [Synthea](https://synthetichealth.github.io/synthea/) for synthetically generated FHIR resources. Both are open-source, although you will need to complete [PhysioNet Credentialing](https://mimic.mit.edu/docs/gettingstarted/) to access MIMIC.

## Loading free-text

You can specify the `free_text_csv` field of the `.generate_prefetch()` method to load in free-text sources into the data generator, e.g. discharge summaries. This will wrap the text into a FHIR [DocumentReference](https://build.fhir.org/documentreference.html) resource (N.B. currently we place the text directly in the resource attachment, although it is technically supposed to be base64 encoded).

A random text document from the `csv` file will be picked for each generation.

```python
# Load free text into a DocumentResource FHIR resource
data = data_generator.generate_prefetch(free_text_csv="./dir/to/csv/file")
```
