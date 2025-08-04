# Sandbox Testing

Sandbox environments provide testing utilities for validating your HealthChain applications in realistic healthcare contexts. These are primarily used for development and testing rather than production deployment.

!!! info "For production applications, use [HealthChainAPI](../gateway/api.md) instead"

    Sandbox is a testing utility. For production healthcare AI applications, use the [Gateway](../gateway/gateway.md) with [HealthChainAPI](../gateway/api.md).

## Quick Example

Test CDS Hooks workflows with synthetic data:

```python
import healthchain as hc
from healthchain.sandbox.use_cases import ClinicalDecisionSupport

@hc.sandbox
class TestCDS(ClinicalDecisionSupport):
    def __init__(self):
        self.pipeline = SummarizationPipeline.from_model_id("facebook/bart-large-cnn")

    @hc.ehr(workflow="encounter-discharge")
    def ehr_database_client(self):
        return self.data_generator.generate_prefetch()

# Run with: healthchain run test_cds.py
```

## Available Testing Scenarios

- **[CDS Hooks](../gateway/cdshooks.md)**: `ClinicalDecisionSupport` - Test clinical decision support workflows
- **[Clinical Documentation](../gateway/soap_cda.md)**: `ClinicalDocumentation` - Test SOAP/CDA document processing workflows

## EHR Client Simulation

The `@hc.ehr` decorator simulates EHR client behavior for testing. You must specify a **workflow** that determines how your data will be formatted.


=== "Clinical Decision Support"
    ```python
    import healthchain as hc
    from healthchain.sandbox.use_cases import ClinicalDecisionSupport
    from healthchain.models import Prefetch
    from fhir.resources.patient import Patient

    @hc.sandbox
    class MyCoolSandbox(ClinicalDecisionSupport):
        @hc.ehr(workflow="patient-view", num=10)
        def load_data_in_client(self) -> Prefetch:
            # Load your test data here
            return Prefetch(prefetch={"patient": Patient(id="123")})
    ```

=== "Clinical Documentation"
    ```python
    import healthchain as hc
    from healthchain.sandbox.use_cases import ClinicalDocumentation
    from healthchain.fhir import create_document_reference
    from fhir.resources.documentreference import DocumentReference

    @hc.sandbox
    class MyCoolSandbox(ClinicalDocumentation):
        @hc.ehr(workflow="sign-note-inpatient", num=10)
        def load_data_in_client(self) -> DocumentReference:
            # Load your test data here
            return create_document_reference(data="", content_type="text/xml")
    ```

**Parameters:**

- `workflow`: The healthcare workflow to simulate (e.g., "patient-view", "sign-note-inpatient")
- `num`: Optional number of requests to generate for testing

## Migration to Production

!!! warning "Sandbox Decorators are Deprecated"
    `@hc.api` is deprecated. Use [HealthChainAPI](../gateway/api.md) for production.

**Quick Migration:**

```python
# Before (Testing) - Shows deprecation warning
@hc.sandbox
class TestCDS(ClinicalDecisionSupport):
    @hc.api  # ⚠️ DEPRECATED
    def my_service(self, request): ...

# After (Production)
from healthchain.gateway import HealthChainAPI, CDSHooksService

app = HealthChainAPI()
cds = CDSHooksService()

@cds.hook("patient-view")
def my_service(request): ...

app.register_service(cds)
```

**Next Steps:**

1. **Testing**: Continue using sandbox utilities with deprecation warnings
2. **Production**: Migrate to [HealthChainAPI Gateway](../gateway/gateway.md)
3. **Protocols**: See [CDS Hooks](../gateway/cdshooks.md) and [SOAP/CDA](../gateway/soap_cda.md)
