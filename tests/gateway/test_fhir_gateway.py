import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle

from healthchain.gateway.fhir import FHIRGateway


class MockConnectionManager:
    """Mock FHIR connection manager for testing."""

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


@pytest.fixture
def mock_connection_manager():
    """Fixture providing a mock connection manager."""
    return MockConnectionManager()


@pytest.fixture
def fhir_gateway(mock_connection_manager):
    """Fixture providing a FHIRGateway with mocked dependencies."""
    with patch(
        "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager",
        return_value=mock_connection_manager,
    ):
        return FHIRGateway(use_events=False)


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
    from fhir.resources.observation import Observation

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
    assert capability.fhirVersion == "4.0.1"


def test_capability_statement_includes_registered_resources(fhir_gateway):
    """CapabilityStatement includes resources with registered handlers."""
    from fhir.resources.observation import Observation

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

    assert status["gateway_type"] == "FHIRGateway"
    assert status["status"] == "active"
    assert isinstance(status["timestamp"], str)
    assert isinstance(status["version"], str)


def test_supported_operations_tracking(fhir_gateway):
    """Gateway accurately tracks registered operations."""
    initial_ops = fhir_gateway.get_gateway_status()["supported_operations"][
        "endpoints"
    ]["transform"]

    @fhir_gateway.transform(Patient)
    def transform_patient(id: str) -> Patient:
        return Patient(id=id)

    updated_status = fhir_gateway.get_gateway_status()

    assert (
        updated_status["supported_operations"]["endpoints"]["transform"]
        == initial_ops + 1
    )
    assert "Patient" in updated_status["supported_operations"]["resources"]


@pytest.mark.asyncio
async def test_read_operation_with_client_delegation(fhir_gateway, test_patient):
    """Read operation delegates to client and handles results correctly."""
    with patch.object(
        fhir_gateway, "_execute_with_client", return_value=test_patient
    ) as mock_execute:
        result = await fhir_gateway.read(Patient, "123", "test_source")

        mock_execute.assert_called_once_with(
            "read",
            source="test_source",
            resource_type=Patient,
            resource_id="123",
            client_args=(Patient, "123"),
        )
        assert result == test_patient


@pytest.mark.asyncio
async def test_read_operation_raises_on_not_found(fhir_gateway):
    """Read operation raises ValueError when resource not found."""
    with patch.object(fhir_gateway, "_execute_with_client", return_value=None):
        with pytest.raises(ValueError, match="Resource Patient/123 not found"):
            await fhir_gateway.read(Patient, "123")


@pytest.mark.asyncio
async def test_create_operation_with_validation(fhir_gateway, test_patient):
    """Create operation validates input and returns created resource."""
    created_patient = Patient(id="456", active=True)
    with patch.object(
        fhir_gateway, "_execute_with_client", return_value=created_patient
    ) as mock_execute:
        result = await fhir_gateway.create(test_patient)

        mock_execute.assert_called_once_with(
            "create",
            source=None,
            resource_type=Patient,
            client_args=(test_patient,),
        )
        assert result == created_patient


@pytest.mark.asyncio
async def test_update_operation_requires_resource_id(fhir_gateway):
    """Update operation validates that resource has ID."""
    patient_without_id = Patient(active=True)  # No ID

    with pytest.raises(ValueError, match="Resource must have an ID for update"):
        await fhir_gateway.update(patient_without_id)


@pytest.mark.asyncio
async def test_search_operation_with_parameters(fhir_gateway):
    """Search operation passes parameters correctly to client."""
    mock_bundle = Bundle(type="searchset", total=1)
    params = {"name": "Smith", "active": "true"}

    with patch.object(
        fhir_gateway, "_execute_with_client", return_value=mock_bundle
    ) as mock_execute:
        result = await fhir_gateway.search(Patient, params, "test_source")

        mock_execute.assert_called_once_with(
            "search",
            source="test_source",
            resource_type=Patient,
            client_args=(Patient,),
            client_kwargs={"params": params},
        )
        assert result == mock_bundle


@pytest.mark.asyncio
async def test_modify_context_for_existing_resource(fhir_gateway, test_patient):
    """Modify context manager fetches, yields, and updates existing resources."""
    mock_client = AsyncMock()
    mock_client.read.return_value = test_patient
    mock_client.update.return_value = Patient(id="123", active=False)

    with patch.object(fhir_gateway, "get_client", return_value=mock_client):
        async with fhir_gateway.modify(Patient, "123") as patient:
            assert patient == test_patient
            patient.active = False

        mock_client.read.assert_called_once_with(Patient, "123")
        mock_client.update.assert_called_once_with(test_patient)


@pytest.mark.asyncio
async def test_modify_context_for_new_resource(fhir_gateway):
    """Modify context manager creates new resources when no ID provided."""
    created_patient = Patient(id="456", active=True)
    mock_client = AsyncMock()
    mock_client.create.return_value = created_patient

    with patch.object(fhir_gateway, "get_client", return_value=mock_client):
        async with fhir_gateway.modify(Patient) as patient:
            assert patient.id is None  # New resource
            patient.active = True

        mock_client.create.assert_called_once()
        # Verify the created resource was updated with returned values
        assert patient.id == "456"


@pytest.mark.asyncio
async def test_execute_with_client_handles_client_errors(fhir_gateway):
    """_execute_with_client properly handles and re-raises client errors."""
    mock_client = AsyncMock()
    mock_client.read.side_effect = Exception("Client error")

    with patch.object(fhir_gateway, "get_client", return_value=mock_client):
        with patch(
            "healthchain.gateway.fhir.errors.FHIRErrorHandler.handle_fhir_error"
        ) as mock_handler:
            mock_handler.side_effect = Exception("Handled error")

            with pytest.raises(Exception, match="Handled error"):
                await fhir_gateway._execute_with_client(
                    "read",
                    resource_type=Patient,
                    resource_id="123",
                    client_args=(Patient, "123"),
                )

            mock_handler.assert_called_once()
