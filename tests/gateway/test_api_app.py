"""Tests for the HealthChainAPI class."""

import pytest
from unittest.mock import AsyncMock
from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError

from healthchain.gateway.api.app import HealthChainAPI
from healthchain.gateway.api.dependencies import (
    get_event_dispatcher,
    get_gateway,
    get_all_gateways,
)
from healthchain.gateway.events.dispatcher import EventDispatcher
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
