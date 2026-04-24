"""Tests for the HealthChainAPI class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError

from healthchain.gateway.api.app import HealthChainAPI
from healthchain.gateway.api.dependencies import (
    get_event_dispatcher,
    get_gateway,
    get_all_gateways,
)
from healthchain.gateway.cds import CDSHooksService
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.gateway.base import BaseGateway


class MockGateway(BaseGateway):
    """Mock gateway for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "MockGateway"
        self.startup_called = False
        self.shutdown_called = False

    async def startup(self):
        self.startup_called = True

    async def shutdown(self):
        self.shutdown_called = True

    def get_metadata(self):
        return {"type": "mock", "version": "1.0.0"}


class MockEventDispatcher(EventDispatcher):
    """Mock event dispatcher for testing."""

    def __init__(self):
        super().__init__()
        self.dispatch = AsyncMock()

    def init_app(self, app):
        pass


@pytest.fixture
def mock_dispatcher():
    return MockEventDispatcher()


@pytest.fixture
def mock_gateway():
    return MockGateway()


@pytest.fixture
def app(mock_dispatcher, mock_gateway):
    """Create test app with mocked dependencies."""
    app = HealthChainAPI(
        title="Test API",
        version="0.1.0",
        enable_events=True,
        event_dispatcher=mock_dispatcher,
    )
    app.register_gateway(mock_gateway)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_app_creation(mock_dispatcher):
    """Test app creation with custom dependencies."""
    app = HealthChainAPI(enable_events=True, event_dispatcher=mock_dispatcher)
    assert app.get_event_dispatcher() is mock_dispatcher
    assert app.enable_events is True


def test_lifespan_startup_shutdown():
    """Test lifespan events call startup and shutdown."""
    gateway = MockGateway()
    app = HealthChainAPI()
    app.register_gateway(gateway)

    with TestClient(app) as client:
        assert gateway.startup_called
        assert client.get("/health").status_code == 200

    assert gateway.shutdown_called


def test_dependency_injection(app, mock_dispatcher, mock_gateway):
    """Test dependency injection works correctly."""

    @app.get("/test-dispatcher")
    def test_dispatcher(dispatcher=Depends(get_event_dispatcher)):
        assert dispatcher is mock_dispatcher
        return {"success": True}

    @app.get("/test-gateway")
    def test_gateway(gateway=Depends(get_gateway)):
        assert gateway is mock_gateway
        return {"success": True}

    @app.get("/test-all-gateways")
    def test_all_gateways(gateways=Depends(get_all_gateways)):
        assert "MockGateway" in gateways
        assert gateways["MockGateway"] is mock_gateway
        return {"success": True}

    with TestClient(app) as client:
        assert client.get("/test-dispatcher").json() == {"success": True}
        assert client.get("/test-gateway?gateway_name=MockGateway").json() == {
            "success": True
        }
        assert client.get("/test-all-gateways").json() == {"success": True}


def test_endpoints(client):
    """Test default API endpoints."""
    # Root endpoint
    root = client.get("/").json()
    assert "MockGateway" in root["gateways"]

    # Health endpoint
    assert client.get("/health").json() == {"status": "healthy"}

    # Metadata endpoint
    metadata = client.get("/metadata").json()
    assert metadata["resourceType"] == "CapabilityStatement"
    assert "MockGateway" in metadata["gateways"]


def test_register_gateway(app):
    """Test gateway registration."""

    class TestGateway(BaseGateway):
        pass

    gateway = TestGateway()
    app.register_gateway(gateway)
    assert "TestGateway" in app.gateways


def test_exception_handling(app):
    """Test unified exception handling."""

    @app.get("/http-error")
    def http_error():
        raise HTTPException(status_code=400, detail="Test error")

    @app.get("/validation-error")
    def validation_error():
        raise RequestValidationError([{"msg": "test validation error"}])

    with TestClient(app) as client:
        # HTTP exception
        response = client.get("/http-error")
        assert response.status_code == 400
        assert response.json() == {"detail": "Test error"}

        # Validation exception
        response = client.get("/validation-error")
        assert response.status_code == 422
        assert "detail" in response.json()


def test_event_dispatcher_integration(mock_dispatcher):
    """Test gateway receives event dispatcher."""
    gateway = MockGateway()
    app = HealthChainAPI(enable_events=True, event_dispatcher=mock_dispatcher)
    app.register_gateway(gateway)
    assert gateway.events.dispatcher is mock_dispatcher


# ── app.sandbox() ──────────────────────────────────────────────────────────────


@pytest.fixture
def cds_app():
    """HealthChainAPI with a registered CDSHooksService and one hook."""
    app = HealthChainAPI(enable_events=False)
    cds = CDSHooksService()

    @cds.hook("patient-view", id="test-hook")
    def handler(request: CDSRequest) -> CDSResponse:
        return CDSResponse(cards=[])

    app.register_service(cds)
    return app


@pytest.fixture
def soap_app():
    """HealthChainAPI with a registered NoteReaderService."""
    from healthchain.gateway.soap.notereader import NoteReaderService
    from healthchain.models.requests.cdarequest import CdaRequest
    from healthchain.models.responses.cdaresponse import CdaResponse

    app = HealthChainAPI(enable_events=False)
    svc = NoteReaderService()

    @svc.method("ProcessDocument")
    def handler(request: CdaRequest) -> CdaResponse:
        return CdaResponse(document="", error=None)

    app.register_service(svc)
    return app


def test_resolve_cds_url_from_service_config(cds_app):
    """URL is built from the registered CDSHooksService base/service paths."""
    url = cds_app._resolve_cds_url("test-hook", "127.0.0.1", 8000)
    assert url == "http://127.0.0.1:8000/cds/cds-services/test-hook"


def test_resolve_cds_url_fallback_when_no_service_registered():
    """Falls back to default CDS path layout when no CDSHooksService is registered."""
    app = HealthChainAPI(enable_events=False)
    url = app._resolve_cds_url("my-hook", "127.0.0.1", 9000)
    assert url == "http://127.0.0.1:9000/cds/cds-services/my-hook"


def test_resolve_soap_url_from_service_config(soap_app):
    """URL is built from the registered NoteReaderService mount path."""
    url = soap_app._resolve_soap_url("127.0.0.1", 8000)
    assert url == "http://127.0.0.1:8000/notereader/?wsdl"


def test_resolve_soap_url_fallback_when_no_service_registered():
    """Falls back to default NoteReader path when no NoteReaderService is registered."""
    app = HealthChainAPI(enable_events=False)
    url = app._resolve_soap_url("127.0.0.1", 8000)
    assert url == "http://127.0.0.1:8000/notereader/?wsdl"


def test_resolve_cds_workflow_returns_hook_type(cds_app):
    """Workflow is resolved from the hook type registered against the given ID."""
    assert cds_app._resolve_cds_workflow("test-hook") == "patient-view"


def test_resolve_cds_workflow_returns_none_for_unknown_id(cds_app):
    """Returns None when no hook matches the given ID."""
    assert cds_app._resolve_cds_workflow("unknown-hook") is None


def test_sandbox_cds_raises_without_hook_id():
    """sandbox() raises ValueError when protocol is CDS and hook_id is omitted."""
    app = HealthChainAPI(enable_events=False)
    with pytest.raises(ValueError, match="hook_id is required"):
        with app.sandbox():
            pass


def test_sandbox_soap_raises_without_workflow(soap_app):
    """sandbox() raises ValueError when protocol is SOAP and workflow is omitted."""
    with pytest.raises(ValueError, match="workflow is required"):
        with soap_app.sandbox(protocol="soap"):
            pass


def test_sandbox_raises_for_unregistered_hook_id(cds_app):
    """sandbox() raises ValueError when the hook ID is not registered."""
    with pytest.raises(ValueError, match="No hook registered"):
        with cds_app.sandbox("nonexistent-hook"):
            pass


def test_sandbox_raises_on_startup_timeout(cds_app):
    """sandbox() raises RuntimeError when the server does not become ready in time."""
    with (
        patch("uvicorn.Server") as mock_server_cls,
        patch("httpx.get", side_effect=ConnectionRefusedError),
    ):
        mock_server = MagicMock()
        mock_server.run = MagicMock()
        mock_server_cls.return_value = mock_server

        with pytest.raises(RuntimeError, match="did not become ready"):
            with cds_app.sandbox("test-hook", startup_timeout=0.1):
                pass
