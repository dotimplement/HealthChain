import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.condition import Condition

from healthchain.gateway.fhir import FHIRGateway
from healthchain.gateway.fhir.errors import FHIRConnectionError
from healthchain.fhir import create_condition


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


def test_read_operation_with_client_delegation(fhir_gateway, test_patient):
    """Read operation delegates to client and handles results correctly."""
    with patch.object(
        fhir_gateway, "_execute_with_client", return_value=test_patient
    ) as mock_execute:
        result = fhir_gateway.read(Patient, "123", "test_source")

        mock_execute.assert_called_once_with(
            "read",
            source="test_source",
            resource_type=Patient,
            resource_id="123",
            client_args=(Patient, "123"),
        )
        assert result == test_patient


def test_read_operation_raises_on_not_found(fhir_gateway):
    """Read operation raises ValueError when resource not found."""
    with patch.object(fhir_gateway, "_execute_with_client", return_value=None):
        with pytest.raises(ValueError, match="Resource Patient/123 not found"):
            fhir_gateway.read(Patient, "123")


def test_create_operation_with_validation(fhir_gateway, test_patient):
    """Create operation validates input and returns created resource."""
    created_patient = Patient(id="456", active=True)
    with patch.object(
        fhir_gateway, "_execute_with_client", return_value=created_patient
    ) as mock_execute:
        result = fhir_gateway.create(test_patient)

        mock_execute.assert_called_once_with(
            "create",
            source=None,
            resource_type=Patient,
            client_args=(test_patient,),
        )
        assert result == created_patient


def test_update_operation_requires_resource_id(fhir_gateway):
    """Update operation validates that resource has ID."""
    patient_without_id = Patient(active=True)  # No ID

    with pytest.raises(ValueError, match="Resource must have an ID for update"):
        fhir_gateway.update(patient_without_id)


def test_search_operation_with_parameters(fhir_gateway):
    """Search operation passes parameters correctly to client."""
    mock_bundle = Bundle(type="searchset", total=1)
    params = {"name": "Smith", "active": "true"}

    with patch.object(
        fhir_gateway, "_execute_with_client", return_value=mock_bundle
    ) as mock_execute:
        result = fhir_gateway.search(Patient, params, "test_source")

        mock_execute.assert_called_once_with(
            "search",
            source="test_source",
            resource_type=Patient,
            client_args=(Patient, params),
        )
        assert result == mock_bundle


def test_execute_with_client_handles_client_errors(fhir_gateway):
    """_execute_with_client properly handles and re-raises client errors."""
    mock_client = Mock()
    mock_client.read.side_effect = Exception("Client error")

    with patch.object(fhir_gateway, "get_client", return_value=mock_client):
        with patch(
            "healthchain.gateway.fhir.errors.FHIRErrorHandler.handle_fhir_error"
        ) as mock_handler:
            mock_handler.side_effect = Exception("Handled error")

            with pytest.raises(Exception, match="Handled error"):
                fhir_gateway._execute_with_client(
                    "read",
                    resource_type=Patient,
                    resource_id="123",
                    client_args=(Patient, "123"),
                )

            mock_handler.assert_called_once()


def test_gateway_handles_source_initialization_errors():
    """FHIRGateway handles errors during source initialization gracefully."""
    # Mock connection manager to raise error on add_source
    mock_manager = Mock()
    mock_manager.add_source.side_effect = FHIRConnectionError(
        code=500, message="Invalid connection string"
    )

    with patch(
        "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager",
        return_value=mock_manager,
    ):
        gateway = FHIRGateway(use_events=False)

        # Should propagate the initialization error
        with pytest.raises(FHIRConnectionError, match="Invalid connection string"):
            gateway.add_source("bad_source", "invalid://connection/string")


def test_gateway_concurrent_operation_resource_management():
    """FHIRGateway manages resources correctly under concurrent access."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    mock_manager = MockConnectionManager()

    with patch(
        "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager",
        return_value=mock_manager,
    ):
        gateway = FHIRGateway(use_events=False)

        # Track concurrent client usage
        client_usage_count = 0
        client_lock = threading.Lock()

        def track_execute(*args, **kwargs):
            nonlocal client_usage_count
            with client_lock:
                client_usage_count += 1
            return Patient(id="test")

        # Execute concurrent operations
        def perform_read():
            with patch.object(
                gateway, "_execute_with_client", side_effect=track_execute
            ):
                return gateway.read(Patient, "123")

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(perform_read) for _ in range(5)]
            results = [future.result() for future in futures]

        # Verify all operations completed successfully
        assert len(results) == 5
        assert all(isinstance(result, Patient) for result in results)

        # Verify concurrent access was tracked
        assert client_usage_count == 5


def test_search_with_auto_provenance():
    """Gateway.search automatically adds provenance metadata when requested."""
    gateway = FHIRGateway()
    gateway.add_source("test_source", "fhir://test.example.com/fhir")

    condition1 = create_condition(
        subject="Patient/123", code="E11.9", display="Type 2 diabetes"
    )
    condition2 = create_condition(
        subject="Patient/123", code="I10", display="Hypertension"
    )

    mock_bundle = Bundle(
        type="searchset",
        entry=[
            BundleEntry(resource=condition1),
            BundleEntry(resource=condition2),
        ],
    )

    mock_client = Mock()
    mock_client.search.return_value = mock_bundle

    with patch.object(gateway, "get_client", return_value=mock_client):
        result = gateway.search(
            Condition,
            {"patient": "Patient/123"},
            "test_source",
            add_provenance=True,
            provenance_tag="aggregated",
        )

        assert result.entry is not None
        assert len(result.entry) == 2
        first_condition = result.entry[0].resource
        assert first_condition.meta is not None
        assert first_condition.meta.source == "urn:healthchain:source:test_source"
        assert first_condition.meta.lastUpdated is not None
        assert first_condition.meta.tag[0].code == "aggregated"
        assert first_condition.meta.tag[0].display == "Aggregated"


def test_search_without_auto_provenance():
    """Gateway.search without auto-provenance leaves resources unchanged."""
    gateway = FHIRGateway()
    gateway.add_source("test_source", "fhir://test.example.com/fhir")

    condition = create_condition(subject="Patient/123", code="E11.9")
    condition.meta = None

    mock_bundle = Bundle(type="searchset", entry=[BundleEntry(resource=condition)])
    mock_client = Mock()
    mock_client.search.return_value = mock_bundle

    with patch.object(gateway, "get_client", return_value=mock_client):
        result = gateway.search(
            Condition, {"patient": "Patient/123"}, "test_source", add_provenance=False
        )
        assert result.entry is not None
        assert len(result.entry) == 1
        assert result.entry[0].resource.meta is None


def test_search_with_empty_bundle():
    """Gateway.search with auto-provenance handles empty bundles gracefully."""
    gateway = FHIRGateway()
    gateway.add_source("test_source", "fhir://test.example.com/fhir")

    mock_bundle = Bundle(type="searchset", entry=None)
    mock_client = Mock()
    mock_client.search.return_value = mock_bundle

    with patch.object(gateway, "get_client", return_value=mock_client):
        result = gateway.search(
            Condition,
            {"patient": "Patient/123"},
            "test_source",
            add_provenance=True,
            provenance_tag="aggregated",
        )
        assert result.entry is None


def test_search_with_pagination(fhir_gateway):
    """Gateway.search fetches all pages when pagination is enabled."""
    # Create mock bundles for pagination
    page1 = Bundle(
        type="searchset",
        entry=[BundleEntry(resource=Patient(id="1"))],
        link=[{"relation": "next", "url": "Patient?page=2"}],
    )
    page2 = Bundle(
        type="searchset",
        entry=[BundleEntry(resource=Patient(id="2"))],
        link=[{"relation": "next", "url": "Patient?page=3"}],
    )
    page3 = Bundle(type="searchset", entry=[BundleEntry(resource=Patient(id="3"))])

    with patch.object(
        fhir_gateway, "_execute_with_client", side_effect=[page1, page2, page3]
    ) as mock_execute:
        result = fhir_gateway.search(Patient, {"name": "Smith"}, follow_pagination=True)

        assert mock_execute.call_count == 3
        assert result.entry is not None
        assert len(result.entry) == 3
        assert [entry.resource.id for entry in result.entry] == ["1", "2", "3"]


def test_search_with_max_pages(fhir_gateway):
    """Gateway.search respects maximum page limit."""
    # Create mock bundles for pagination
    page1 = Bundle(
        type="searchset",
        entry=[BundleEntry(resource=Patient(id="1"))],
        link=[{"relation": "next", "url": "Patient?page=2"}],
    )
    page2 = Bundle(
        type="searchset",
        entry=[BundleEntry(resource=Patient(id="2"))],
        link=[{"relation": "next", "url": "Patient?page=3"}],
    )

    with patch.object(
        fhir_gateway, "_execute_with_client", side_effect=[page1, page2]
    ) as mock_execute:
        result = fhir_gateway.search(
            Patient, {"name": "Smith"}, follow_pagination=True, max_pages=2
        )

        assert mock_execute.call_count == 2
        assert result.entry is not None
        assert len(result.entry) == 2
        assert [entry.resource.id for entry in result.entry] == ["1", "2"]


def test_search_with_pagination_empty_next_link(fhir_gateway):
    """Gateway.search handles missing next links correctly."""
    # Create mock bundle without next link
    bundle = Bundle(
        type="searchset",
        entry=[BundleEntry(resource=Patient(id="1"))],
        link=[{"relation": "self", "url": "Patient?name=Smith"}],
    )

    with patch.object(
        fhir_gateway, "_execute_with_client", return_value=bundle
    ) as mock_execute:
        result = fhir_gateway.search(Patient, {"name": "Smith"}, follow_pagination=True)

        mock_execute.assert_called_once()
        assert result.entry is not None
        assert len(result.entry) == 1
        assert result.entry[0].resource.id == "1"


def test_search_with_pagination_and_provenance(fhir_gateway):
    """Gateway.search combines pagination with provenance metadata."""
    page1 = Bundle(
        type="searchset",
        entry=[BundleEntry(resource=Patient(id="1"))],
        link=[{"relation": "next", "url": "Patient?page=2"}],
    )
    page2 = Bundle(type="searchset", entry=[BundleEntry(resource=Patient(id="2"))])

    with patch.object(
        fhir_gateway, "_execute_with_client", side_effect=[page1, page2]
    ) as mock_execute:
        result = fhir_gateway.search(
            Patient,
            {"name": "Smith"},
            source="test_source",
            follow_pagination=True,
            add_provenance=True,
            provenance_tag="aggregated",
        )

        assert mock_execute.call_count == 2
        assert result.entry is not None
        assert len(result.entry) == 2

        # Check provenance metadata
        for entry in result.entry:
            assert entry.resource.meta is not None
            assert entry.resource.meta.source == "urn:healthchain:source:test_source"
            assert entry.resource.meta.tag[0].code == "aggregated"
