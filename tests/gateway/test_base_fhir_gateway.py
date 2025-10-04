import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List
import asyncio

from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.riskassessment import RiskAssessment

from healthchain.gateway.fhir import FHIRGateway, AsyncFHIRGateway


class MockConnectionManager:
    """Mock FHIR connection manager for testing."""

    def __init__(self):
        self.sources = {"test_source": Mock()}

    def add_source(self, name: str, connection_string: str) -> None:
        self.sources[name] = Mock()

    def get_client(self, source: str = None):
        return Mock()

    def get_status(self) -> Dict[str, Any]:
        return {
            "max_connections": 100,
            "sources": {"test_source": "connected"},
        }


class MockAsyncConnectionManager:
    """Mock async FHIR connection manager for testing."""

    def __init__(self):
        self.sources = {"test_source": Mock()}

    def add_source(self, name: str, connection_string: str) -> None:
        self.sources[name] = Mock()

    async def get_client(self, source: str = None):
        return AsyncMock()

    def get_pool_status(self) -> Dict[str, Any]:
        return {
            "max_connections": 100,
            "sources": {"test_source": "connected"},
        }

    async def close(self) -> None:
        pass


@pytest.fixture(params=["sync", "async"])
def fhir_gateway(request):
    """Fixture providing both sync and async FHIR gateways."""
    if request.param == "sync":
        with patch(
            "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager",
            return_value=MockConnectionManager(),
        ):
            return FHIRGateway(use_events=False)
    else:
        with patch(
            "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager",
            return_value=MockAsyncConnectionManager(),
        ):
            return AsyncFHIRGateway(use_events=False)


@pytest.fixture
def test_patient():
    """Fixture providing a test Patient resource."""
    return Patient(id="123", active=True)


def test_transform_handler_registration_with_correct_annotation(fhir_gateway):
    """Transform handlers with correct return type annotations register successfully."""

    @fhir_gateway.transform(Patient)
    def transform_patient(id: str, source: str = None) -> Patient:
        return Patient(id=id)

    assert fhir_gateway._resource_handlers[Patient]["transform"] == transform_patient


def test_transform_handler_validation_enforces_return_type_match(fhir_gateway):
    """Transform handler registration validates return type matches decorator resource type."""

    with pytest.raises(
        TypeError, match="return type .* doesn't match decorator resource type"
    ):

        @fhir_gateway.transform(Patient)
        def invalid_handler(id: str) -> Observation:  # Wrong return type
            return Observation()


def test_aggregate_handler_registration_without_validation(fhir_gateway):
    """Aggregate handlers register without return type validation."""

    @fhir_gateway.aggregate(Patient)
    def aggregate_patients(id: str = None, sources: List[str] = None):
        return []

    assert fhir_gateway._resource_handlers[Patient]["aggregate"] == aggregate_patients


def test_handler_registration_creates_routes(fhir_gateway):
    """Handler registration automatically creates corresponding API routes."""
    initial_routes = len(fhir_gateway.routes)

    @fhir_gateway.transform(Patient)
    def transform_patient(id: str) -> Patient:
        return Patient(id=id)

    assert len(fhir_gateway.routes) == initial_routes + 1


def test_empty_capability_statement_with_no_handlers(fhir_gateway):
    """Gateway with no handlers generates minimal CapabilityStatement."""
    capability = fhir_gateway.build_capability_statement()

    assert capability.model_dump()["resourceType"] == "CapabilityStatement"
    assert capability.status == "active"
    assert capability.kind == "instance"


def test_capability_statement_includes_registered_resources(fhir_gateway):
    """CapabilityStatement includes resources with registered handlers."""

    @fhir_gateway.transform(Patient)
    def transform_patient(id: str) -> Patient:
        return Patient(id=id)

    @fhir_gateway.aggregate(Observation)
    def aggregate_observations(id: str = None) -> List[Observation]:
        return []

    capability = fhir_gateway.build_capability_statement()
    resources = capability.rest[0].resource
    resource_types = [r.type for r in resources]

    assert "Patient" in resource_types
    assert "Observation" in resource_types


def test_gateway_status_structure(fhir_gateway):
    """Gateway status contains required fields with correct structure."""
    status = fhir_gateway.get_gateway_status()

    # Gateway type should match the actual class name
    expected_type = (
        "AsyncFHIRGateway"
        if isinstance(fhir_gateway, AsyncFHIRGateway)
        else "FHIRGateway"
    )
    assert status["gateway_type"] == expected_type
    assert status["status"] == "active"
    assert isinstance(status["timestamp"], str)
    assert isinstance(status["version"], str)


def test_supported_operations_tracking(fhir_gateway):
    """Gateway accurately tracks registered operations."""
    # Get initial status - should have no operations
    initial_status = fhir_gateway.get_gateway_status()
    assert initial_status["supported_operations"] == {}

    @fhir_gateway.transform(Patient)
    def transform_patient(id: str) -> Patient:
        return Patient(id=id)

    updated_status = fhir_gateway.get_gateway_status()

    # Check that Patient transform operation is now tracked
    assert "Patient" in updated_status["supported_operations"]
    patient_ops = updated_status["supported_operations"]["Patient"]
    assert len(patient_ops) == 1
    assert patient_ops[0]["type"] == "transform"
    assert patient_ops[0]["endpoint"] == "/transform/Patient/{id}"


def test_supported_resources_property(fhir_gateway):
    """supported_resources property returns correct resource names."""
    # Initially no resources
    assert fhir_gateway.supported_resources == []

    @fhir_gateway.transform(Patient)
    def transform_patient(id: str) -> Patient:
        return Patient(id=id)

    @fhir_gateway.aggregate(Observation)
    def aggregate_observations() -> List[Observation]:
        return []

    supported = fhir_gateway.supported_resources
    assert "Patient" in supported
    assert "Observation" in supported


def test_get_capabilities_method(fhir_gateway):
    """get_capabilities method returns correct operation:resource pairs."""
    # Initially no capabilities
    assert fhir_gateway.get_capabilities() == []

    @fhir_gateway.transform(Patient)
    def transform_patient(id: str) -> Patient:
        return Patient(id=id)

    @fhir_gateway.aggregate(Patient)
    def aggregate_patients() -> List[Patient]:
        return []

    capabilities = fhir_gateway.get_capabilities()
    assert "transform:Patient" in capabilities
    assert "aggregate:Patient" in capabilities


def test_resource_name_extraction(fhir_gateway):
    """_get_resource_name correctly extracts resource names from types."""
    assert fhir_gateway._get_resource_name(Patient) == "Patient"
    assert fhir_gateway._get_resource_name(Observation) == "Observation"


@pytest.mark.asyncio
async def test_predict_handler_raises_for_invalid_output_type(fhir_gateway):
    """The predict route handler should raise a TypeError for unsupported return types."""

    @fhir_gateway.predict(resource=RiskAssessment)
    def invalid_prediction(patient_id: str) -> list:
        return [0.1, 0.9]  # Invalid return type

    route_handler = fhir_gateway.routes[-1].endpoint

    with pytest.raises(TypeError, match="Prediction function must return a float or dict"):
        await route_handler(id="Patient789", fhir=fhir_gateway)


def test_predict_decorator_registers_handler_and_route(fhir_gateway):
    """The @predict decorator should register a 'predict' handler and create a route."""
    initial_routes = len(fhir_gateway.routes)

    @fhir_gateway.predict(resource=RiskAssessment)
    def predict_risk(patient_id: str) -> float:
        return 0.5

    # Check handler registration
    assert "predict" in fhir_gateway._resource_handlers[RiskAssessment]
    assert (
        fhir_gateway._resource_handlers[RiskAssessment]["predict"]
        == predict_risk
    )
    # Check that decorator kwargs are stored
    assert "predict_kwargs" in fhir_gateway._resource_handlers[RiskAssessment]
    assert fhir_gateway._resource_handlers[RiskAssessment]["predict_kwargs"] == {
        "status": "final"
    }

    # Check route creation
    assert len(fhir_gateway.routes) == initial_routes + 1
    new_route = fhir_gateway.routes[-1]
    assert new_route.path == "/predict/RiskAssessment/{id}"


@pytest.mark.asyncio
async def test_predict_handler_wraps_float_output(fhir_gateway):
    """The predict route handler should wrap a float from a sync function into a FHIR resource."""

    @fhir_gateway.predict(resource=RiskAssessment)
    def simple_prediction(patient_id: str) -> float:
        return 0.75

    # The handler created by _create_route_handler is what we need to test
    # It's an async function that wraps the user's sync function
    route_handler = fhir_gateway.routes[-1].endpoint
    result = await route_handler(id="Patient123", fhir=fhir_gateway)

    assert isinstance(result, RiskAssessment)
    assert result.status == "final"
    assert result.subject.reference == "Patient/Patient123"
    assert result.prediction[0].probabilityDecimal == 0.75


@pytest.mark.asyncio
async def test_predict_handler_wraps_dict_output_from_async_func(fhir_gateway):
    """The predict route handler should wrap a dict from an async function into a FHIR resource."""

    @fhir_gateway.predict(resource=RiskAssessment)
    async def complex_prediction(patient_id: str) -> dict:
        await asyncio.sleep(0.01)  # Simulate async work
        return {"score": 0.4, "qualitativeRisk": "low"}

    route_handler = fhir_gateway.routes[-1].endpoint
    result = await route_handler(id="Patient456", fhir=fhir_gateway)

    assert isinstance(result, RiskAssessment)
    assert result.subject.reference == "Patient/Patient456"
    assert result.prediction[0].probabilityDecimal == 0.4
    assert result.prediction[0].qualitativeRisk == "low"


def test_predict_decorator_in_capability_statement(fhir_gateway):
    """CapabilityStatement should include resources with registered predict handlers."""

    @fhir_gateway.predict(resource=RiskAssessment)
    def predict_risk(patient_id: str) -> float:
        return 0.5

    capability = fhir_gateway.build_capability_statement()
    resources = capability.rest[0].resource
    assert "RiskAssessment" in [r.type for r in resources]
