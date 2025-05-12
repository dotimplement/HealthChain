from unittest.mock import patch, MagicMock

import healthchain as hc
from healthchain.gateway.services.cdshooks import CDSHooksService
from healthchain.gateway.api import HealthChainAPI
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse, Card
from healthchain.models.hooks.prefetch import Prefetch
from healthchain.sandbox.use_cases import ClinicalDecisionSupport
from healthchain.fhir import create_bundle, create_condition


def test_cdshooks_sandbox_integration():
    """Test CDSHooks service integration with sandbox decorator"""
    # Create HealthChainAPI instead of FastAPI
    app = HealthChainAPI()
    cds_service = CDSHooksService()

    # Register a hook handler for the service
    @cds_service.hook("patient-view", id="test-patient-view")
    async def handle_patient_view(request: CDSRequest) -> CDSResponse:
        return CDSResponse(
            cards=[
                Card(summary="Test Card", indicator="info", source={"label": "Test"})
            ]
        )

    # Register the service with the HealthChainAPI
    app.register_service(cds_service, "/cds")

    # Define a sandbox class using the CDSHooks service
    @hc.sandbox("http://localhost:8000/")
    class TestCDSHooksSandbox(ClinicalDecisionSupport):
        def __init__(self):
            super().__init__(path="/cds/cds-services/")
            self.test_bundle = create_bundle()

        @hc.ehr(workflow="patient-view")
        def load_prefetch_data(self) -> Prefetch:
            return Prefetch(prefetch={"patient": self.test_bundle})

    # Create an instance of the sandbox
    sandbox_instance = TestCDSHooksSandbox()

    # Patch the client request method to avoid actual HTTP requests
    with patch.object(sandbox_instance, "_client") as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "cards": [
                {
                    "summary": "Test Card",
                    "indicator": "info",
                    "source": {"label": "Test"},
                }
            ]
        }
        mock_client.send_request.return_value = mock_response

        # Verify the sandbox can be initialized with the workflow
        assert hasattr(sandbox_instance, "load_prefetch_data")


def test_cdshooks_workflows():
    """Test CDSHooks sandbox"""

    @hc.sandbox("http://localhost:8000/")
    class TestCDSSandbox(ClinicalDecisionSupport):
        def __init__(self):
            super().__init__(path="/cds/cds-services/")
            self.patient_bundle = create_bundle()
            self.encounter_bundle = create_bundle()

        @hc.ehr(workflow="patient-view")
        def load_patient_data(self) -> Prefetch:
            # Add a condition to the bundle
            condition = create_condition(
                subject="Patient/123", code="123", display="Test Condition"
            )
            self.patient_bundle.entry = [{"resource": condition}]
            return Prefetch(prefetch={"patient": self.patient_bundle})

    # Create sandbox instance
    sandbox = TestCDSSandbox()

    # Verify both workflows are correctly registered
    assert hasattr(sandbox, "load_patient_data")

    # Test the patient-view workflow
    with patch.object(sandbox, "_client") as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = {"cards": []}
        mock_client.send_request.return_value = mock_response

        # Mock client workflow
        mock_client.workflow = MagicMock()
        mock_client.workflow.value = "patient-view"
