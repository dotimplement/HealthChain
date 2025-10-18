"""Integration tests for HealthChain API HTTP endpoints."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.anyio


@pytest.fixture
def client(configured_app):
    """FastAPI TestClient for API testing."""
    return TestClient(configured_app)


@pytest.mark.parametrize(
    "endpoint,expected_fields",
    [
        ("/", ["name", "version", "gateways", "services"]),
        ("/metadata", ["resourceType", "status", "gateways", "services"]),
    ],
)
def test_api_metadata_endpoints(client, endpoint, expected_fields):
    """API metadata endpoints return expected structure."""
    response = client.get(endpoint)
    assert response.status_code == 200
    data = response.json()
    for field in expected_fields:
        assert field in data


def test_health_check_returns_healthy_status(client):
    """Health check endpoint returns healthy status with registered services."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.parametrize(
    "endpoint,expected_resource_type,expected_kind",
    [
        ("/metadata", "CapabilityStatement", None),
        ("/fhir/metadata", "CapabilityStatement", "instance"),
    ],
)
def test_fhir_capability_statements(
    client, endpoint, expected_resource_type, expected_kind
):
    """FHIR metadata endpoints return valid CapabilityStatement resources."""
    response = client.get(endpoint)
    assert response.status_code == 200
    data = response.json()
    assert data["resourceType"] == expected_resource_type
    if expected_kind:
        assert data["kind"] == expected_kind
        assert "rest" in data


def test_fhir_gateway_status(client):
    """FHIR status endpoint returns gateway operational details."""
    response = client.get("/fhir/status")
    assert response.status_code == 200
    data = response.json()
    assert data["gateway_type"] == "FHIRGateway"
    assert data["status"] == "active"
    assert "supported_operations" in data
    # Verify operations are organized by resource type
    assert "DocumentReference" in data["supported_operations"]
    assert "Patient" in data["supported_operations"]


def test_fhir_transform_applies_ai_enhancements(client):
    """FHIR transform endpoint enhances DocumentReference with AI extensions."""
    response = client.get("/fhir/transform/DocumentReference/test-id?source=demo")

    assert response.status_code == 200
    assert "application/fhir+json" in response.headers["content-type"]
    data = response.json()
    assert data["resourceType"] == "DocumentReference"

    # Verify AI enhancement applied
    assert data["extension"]
    assert any("ai-summary" in ext["url"] for ext in data["extension"])
    assert data["meta"]["tag"][0]["code"] == "ai-enhanced"


def test_fhir_aggregate_combines_patient_data(client):
    """FHIR aggregate endpoint merges Patient data from multiple sources."""
    response = client.get(
        "/fhir/aggregate/Patient?id=test-patient&sources=demo&sources=epic"
    )

    assert response.status_code == 200
    assert "application/fhir+json" in response.headers["content-type"]
    data = response.json()
    assert data["resourceType"] == "Patient"
    assert data["id"] == "test-patient"


def test_cds_discovery_returns_available_services(client):
    """CDS Hooks discovery endpoint exposes registered service definitions."""
    response = client.get("/cds/cds-discovery")

    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert len(data["services"]) == 1

    # Verify service configuration
    service = data["services"][0]
    assert service["hook"] == "encounter-discharge"
    assert service["id"] == "discharge-summary"


def test_cds_service_processes_hook_request(client, test_cds_response_single_card):
    """CDS Hooks service endpoint processes requests and returns cards."""
    request_data = {
        "hook": "encounter-discharge",
        "hookInstance": "test-instance",
        "context": {"patientId": "123", "userId": "Practitioner/1"},
    }

    response = client.post("/cds/cds-services/discharge-summary", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    assert len(data["cards"]) == 1
    assert data["cards"][0]["summary"] == test_cds_response_single_card.cards[0].summary
