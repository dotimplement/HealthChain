"""
Tests for the HealthChainAPI class with dependency injection.

This module contains tests for the HealthChainAPI class, focusing on
testing with dependency injection.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi import Depends, APIRouter, HTTPException
from fastapi.testclient import TestClient

from healthchain.gateway.api.app import create_app
from healthchain.gateway.api.dependencies import (
    get_app,
    get_event_dispatcher,
    get_gateway,
    get_all_gateways,
)
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.gateway.core.base import BaseGateway


class MockGateway(BaseGateway):
    """Mock gateway for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "MockGateway"
        self.event_dispatcher = None

    def get_metadata(self):
        return {"type": "mock", "version": "1.0.0"}

    def set_event_dispatcher(self, dispatcher):
        self.event_dispatcher = dispatcher


class AnotherMockGateway(BaseGateway):
    """Another mock gateway for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "AnotherMockGateway"


class MockEventDispatcher(EventDispatcher):
    """Mock event dispatcher for testing."""

    def __init__(self):
        super().__init__()
        self.dispatch = AsyncMock()

    def init_app(self, app):
        pass


@pytest.fixture
def mock_event_dispatcher():
    """Create a mock event dispatcher."""
    return MockEventDispatcher()


@pytest.fixture
def mock_gateway():
    """Create a mock gateway."""
    return MockGateway()


@pytest.fixture
def test_app(mock_event_dispatcher, mock_gateway):
    """Create a test app with mocked dependencies."""
    app = create_app(enable_events=True, event_dispatcher=mock_event_dispatcher)
    app.register_gateway(mock_gateway)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


def test_app_creation():
    """Test that the app can be created with custom dependencies."""
    mock_dispatcher = MockEventDispatcher()
    app = create_app(enable_events=True, event_dispatcher=mock_dispatcher)

    assert app.get_event_dispatcher() is mock_dispatcher
    assert app.enable_events is True


def test_dependency_injection_get_app(test_app):
    """Test that get_app dependency returns the app."""
    # Override dependency to return our test app
    test_app.dependency_overrides[get_app] = lambda: test_app

    with TestClient(test_app) as client:
        response = client.get("/health")
        assert response.status_code == 200


def test_dependency_injection_event_dispatcher(test_app, mock_event_dispatcher):
    """Test that get_event_dispatcher dependency returns the event dispatcher."""

    # Create a test route that uses the dependency
    @test_app.get("/test-event-dispatcher")
    def test_route(dispatcher=Depends(get_event_dispatcher)):
        assert dispatcher is mock_event_dispatcher
        return {"success": True}

    with TestClient(test_app) as client:
        response = client.get("/test-event-dispatcher")
        assert response.status_code == 200
        assert response.json() == {"success": True}


def test_dependency_injection_gateway(test_app, mock_gateway):
    """Test that get_gateway dependency returns the gateway."""

    # Create a test route that uses the dependency
    @test_app.get("/test-gateway/{gateway_name}")
    def test_route(gateway_name: str, gateway=Depends(get_gateway)):
        assert gateway is mock_gateway
        return {"success": True}

    with TestClient(test_app) as client:
        response = client.get("/test-gateway/MockGateway")
        assert response.status_code == 200
        assert response.json() == {"success": True}


def test_dependency_injection_all_gateways(test_app, mock_gateway):
    """Test that get_all_gateways dependency returns all gateways."""

    # Create a test route that uses the dependency
    @test_app.get("/test-all-gateways")
    def test_route(gateways=Depends(get_all_gateways)):
        assert "MockGateway" in gateways
        assert gateways["MockGateway"] is mock_gateway
        return {"success": True}

    with TestClient(test_app) as client:
        response = client.get("/test-all-gateways")
        assert response.status_code == 200
        assert response.json() == {"success": True}


def test_root_endpoint(client):
    """Test the root endpoint returns gateway information."""
    response = client.get("/")
    assert response.status_code == 200
    assert "MockGateway" in response.json()["gateways"]


def test_metadata_endpoint(client):
    """Test the metadata endpoint returns gateway information."""
    response = client.get("/metadata")
    assert response.status_code == 200

    data = response.json()
    assert data["resourceType"] == "CapabilityStatement"
    assert "MockGateway" in data["gateways"]
    assert data["gateways"]["MockGateway"]["type"] == "mock"


def test_register_gateway(test_app):
    """Test registering a gateway."""
    # Create a gateway instance
    another_gateway = AnotherMockGateway()

    # Register it with the app
    test_app.register_gateway(another_gateway)

    # Verify it was registered
    assert "AnotherMockGateway" in test_app.gateways
    assert test_app.gateways["AnotherMockGateway"] is another_gateway


def test_register_router(test_app):
    """Test registering a router."""
    # Create a router
    router = APIRouter(prefix="/test-router", tags=["test"])

    @router.get("/test")
    def test_route():
        return {"message": "Router test"}

    # Register the router
    test_app.register_router(router)

    # Test the route
    with TestClient(test_app) as client:
        response = client.get("/test-router/test")
        assert response.status_code == 200
        assert response.json() == {"message": "Router test"}


def test_exception_handling(test_app):
    """Test the exception handling middleware."""

    # Add a route that raises an exception
    @test_app.get("/test-error")
    async def error_route():
        raise HTTPException(status_code=400, detail="Test error")

    # Add a route that raises an unexpected exception
    @test_app.get("/test-unexpected-error")
    async def unexpected_error_route():
        raise ValueError("Unexpected test error")

    with TestClient(test_app) as client:
        # Test HTTP exception handling
        response = client.get("/test-error")
        assert response.status_code == 400
        assert response.json() == {"detail": "Test error"}

        # Test unexpected exception handling
        with pytest.raises(ValueError):
            response = client.get("/test-unexpected-error")
            assert response.status_code == 500
            assert response.json() == {"detail": "Internal server error"}


def test_gateway_event_dispatcher_integration(mock_event_dispatcher):
    """Test that gateways receive the event dispatcher when registered."""
    # Create a gateway
    gateway = MockGateway()

    # Create app with events enabled
    app = create_app(enable_events=True, event_dispatcher=mock_event_dispatcher)

    # Register gateway
    app.register_gateway(gateway)

    # Check that gateway received the event dispatcher
    assert gateway.event_dispatcher is mock_event_dispatcher
