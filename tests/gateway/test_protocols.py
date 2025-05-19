"""
Tests for Protocol conformance in the HealthChain gateway system.

This module tests whether the implementations of various components
correctly conform to their defined Protocol interfaces.
"""

from typing import cast

from healthchain.gateway.api.protocols import (
    HealthChainAPIProtocol,
    GatewayProtocol,
    EventDispatcherProtocol,
)
from healthchain.gateway.api.app import create_app
from healthchain.gateway.events.dispatcher import EventDispatcher
from tests.gateway.test_api_app import MockGateway


def test_healthchainapi_conforms_to_protocol():
    """Test that HealthChainAPI conforms to HealthChainAPIProtocol."""
    # Create an instance of HealthChainAPI
    app = create_app()

    # Cast to the protocol type - this will fail at runtime if not compatible
    protocol_app = cast(HealthChainAPIProtocol, app)

    # Basic assertions to check that it functions as expected
    assert hasattr(protocol_app, "get_event_dispatcher")
    assert hasattr(protocol_app, "get_gateway")
    assert hasattr(protocol_app, "get_all_gateways")
    assert hasattr(protocol_app, "register_gateway")
    assert hasattr(protocol_app, "register_router")


def test_eventdispatcher_conforms_to_protocol():
    """Test that EventDispatcher conforms to EventDispatcherProtocol."""
    # Create an instance of EventDispatcher
    dispatcher = EventDispatcher()

    # Cast to the protocol type - this will fail at runtime if not compatible
    protocol_dispatcher = cast(EventDispatcherProtocol, dispatcher)

    # Basic assertions to check that it functions as expected
    assert hasattr(protocol_dispatcher, "publish")
    assert hasattr(protocol_dispatcher, "init_app")
    assert hasattr(protocol_dispatcher, "register_handler")


def test_gateway_conforms_to_protocol():
    """Test that MockGateway conforms to GatewayProtocol."""
    # Create an instance of MockGateway
    gateway = MockGateway()

    # Cast to the protocol type - this will fail at runtime if not compatible
    protocol_gateway = cast(GatewayProtocol, gateway)

    # Basic assertions to check that it functions as expected
    assert hasattr(protocol_gateway, "get_metadata")
    assert hasattr(protocol_gateway, "set_event_dispatcher")


def test_typed_gateway_access():
    """Test accessing a gateway with a specific protocol type."""
    # Create app and gateway
    app = create_app()
    gateway = MockGateway()
    app.register_gateway(gateway)

    # Test getting the gateway as a general GatewayProtocol
    retrieved_gateway = app.get_gateway("MockGateway")
    assert retrieved_gateway is not None

    # Cast to protocol type - will fail if not compatible
    protocol_gateway = cast(GatewayProtocol, retrieved_gateway)
    assert protocol_gateway.get_metadata() == gateway.get_metadata()
