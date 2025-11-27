from unittest.mock import patch, MagicMock

from healthchain.sandbox import SandboxClient
from healthchain.gateway.cds import CDSHooksService
from healthchain.gateway.api import HealthChainAPI
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse, Card
from healthchain.fhir import create_bundle, create_condition


def test_cdshooks_sandbox_integration():
    """Test CDSHooks service integration with SandboxClient"""
    # Create HealthChainAPI
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

    # Create SandboxClient
    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/test-patient-view",
        workflow="patient-view",
        protocol="rest",
    )

    # Load test data
    test_bundle = create_bundle()
    prefetch_data = {"patient": test_bundle}
    client._construct_request(prefetch_data)

    # Verify request was constructed
    assert len(client.requests) == 1
    assert client.requests[0].hook == "patient-view"

    # Mock HTTP response
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

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
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        # Send requests
        responses = client.send_requests()

        # Verify response
        assert len(responses) == 1
        assert responses[0]["cards"][0]["summary"] == "Test Card"


def test_cdshooks_workflows():
    """Test CDSHooks sandbox with patient-view workflow"""
    # Create SandboxClient
    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/patient-view",
        workflow="patient-view",
        protocol="rest",
    )

    # Create test data
    patient_bundle = create_bundle()
    condition = create_condition(
        subject="Patient/123", code="123", display="Test Condition"
    )
    patient_bundle.entry = [{"resource": condition}]

    # Load data into client
    prefetch_data = {"patient": patient_bundle}
    client._construct_request(prefetch_data)

    # Verify request was constructed
    assert len(client.requests) == 1

    # Mock HTTP response
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.json.return_value = {"cards": []}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        # Send requests and verify
        responses = client.send_requests()
        assert len(responses) == 1
        assert "cards" in responses[0]
