"""
Tests for the core base classes in the HealthChain gateway system.

This module tests the fundamental base classes that define the gateway architecture:
- BaseGateway
- BaseProtocolHandler
- EventCapability
- GatewayConfig
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from healthchain.gateway.base import (
    BaseGateway,
    BaseProtocolHandler,
    EventCapability,
    GatewayConfig,
)
from healthchain.gateway.events.dispatcher import EventDispatcher

# Configure pytest-asyncio for async tests


@pytest.fixture
def mock_event_dispatcher():
    """Create a mock event dispatcher for testing."""
    dispatcher = Mock(spec=EventDispatcher)
    dispatcher.publish = AsyncMock()
    dispatcher.register_handler = Mock(return_value=lambda f: f)
    return dispatcher


class ConcreteProtocolHandler(BaseProtocolHandler[Dict[str, Any], Dict[str, Any]]):
    """Concrete implementation of BaseProtocolHandler for testing."""

    def _process_result(self, result: Any) -> Dict[str, Any]:
        """Process results into expected dict format."""
        if isinstance(result, dict):
            return result
        return {"processed": str(result)}


class ConcreteGateway(BaseGateway):
    """Concrete implementation of BaseGateway for testing."""

    def get_metadata(self) -> Dict[str, Any]:
        metadata = super().get_metadata()
        metadata["test_specific"] = True
        return metadata


def test_event_capability_configuration_and_chaining(mock_event_dispatcher):
    """EventCapability supports configuration and method chaining."""
    capability = EventCapability()
    mock_creator = Mock(return_value={"event": "test"})

    # Test method chaining and configuration
    result = capability.set_dispatcher(mock_event_dispatcher).set_event_creator(
        mock_creator
    )

    assert capability.dispatcher == mock_event_dispatcher
    assert capability._event_creator == mock_creator
    assert result == capability  # Method chaining


def test_event_capability_delegated_publishing(mock_event_dispatcher):
    """EventCapability delegates to dispatcher's emit method."""
    capability = EventCapability()
    capability.set_dispatcher(mock_event_dispatcher)

    test_event = {"type": "test_event"}
    capability.publish(test_event)

    mock_event_dispatcher.emit.assert_called_once_with(test_event)


@pytest.mark.asyncio
async def test_protocol_handler_supports_sync_and_async_handlers():
    """BaseProtocolHandler supports both synchronous and asynchronous handlers."""
    handler = ConcreteProtocolHandler()

    # Register handlers
    handler.register_handler("sync_op", lambda data: {"sync_result": data})
    handler.register_handler(
        "async_op", AsyncMock(return_value={"async_result": "test"})
    )

    # Test both handler types
    sync_result = await handler.handle("sync_op", data="test_sync")
    async_result = await handler.handle("async_op", data="test_async")

    assert sync_result == {"sync_result": "test_sync"}
    assert async_result == {"async_result": "test"}


@pytest.mark.parametrize(
    "return_errors,operation_exists,expected_behavior",
    [
        # Handler exists - should succeed
        (False, True, {"success": True, "raises": False}),
        (True, True, {"success": True, "raises": False}),
        # Handler missing, return_errors=False - should raise
        (False, False, {"success": False, "raises": True}),
        # Handler missing, return_errors=True - should return error dict
        (True, False, {"success": False, "raises": False, "error_in_response": True}),
    ],
)
@pytest.mark.asyncio
async def test_protocol_handler_error_handling_behavior(
    return_errors, operation_exists, expected_behavior
):
    """BaseProtocolHandler handles missing operations and errors according to configuration."""
    config = GatewayConfig(return_errors=return_errors)
    handler = ConcreteProtocolHandler(config=config)

    if operation_exists:
        handler.register_handler("test_op", lambda data: {"result": data})

    if expected_behavior["raises"]:
        with pytest.raises(ValueError, match="Unsupported operation"):
            await handler.handle(
                "test_op" if operation_exists else "missing_op", data="test"
            )
    else:
        result = await handler.handle(
            "test_op" if operation_exists else "missing_op", data="test"
        )

        if expected_behavior.get("error_in_response"):
            assert "error" in result
            assert "Unsupported operation" in result["error"]
        else:
            assert result == {"result": "test"}


@pytest.mark.asyncio
async def test_protocol_handler_exception_handling_in_handlers():
    """BaseProtocolHandler handles exceptions in registered handlers appropriately."""
    # Test with return_errors=False (should raise)
    handler_raise = ConcreteProtocolHandler(config=GatewayConfig(return_errors=False))
    handler_raise.register_handler("failing_op", lambda: 1 / 0)

    with pytest.raises(ValueError, match="Error during operation execution"):
        await handler_raise.handle("failing_op")

    # Test with return_errors=True (should return error dict)
    handler_return = ConcreteProtocolHandler(config=GatewayConfig(return_errors=True))
    handler_return.register_handler("failing_op", lambda: 1 / 0)

    result = await handler_return.handle("failing_op")
    assert "error" in result
    assert "Error during operation execution" in result["error"]


def test_base_gateway_initialization_and_metadata_generation():
    """BaseGateway initializes correctly and generates metadata including event capabilities."""
    # Test default initialization
    gateway = ConcreteGateway()
    assert gateway.prefix == "/api"
    assert gateway.tags == []

    # Test custom initialization and metadata
    custom_gateway = ConcreteGateway(
        prefix="/custom", tags=["test"], config=GatewayConfig(system_type="TEST_SYSTEM")
    )

    assert custom_gateway.prefix == "/custom"
    assert custom_gateway.tags == ["test"]

    # Test metadata generation
    metadata = custom_gateway.get_gateway_status()
    assert metadata["gateway_type"] == "ConcreteGateway"
    assert metadata["system_type"] == "TEST_SYSTEM"
    assert metadata["status"] == "active"

    # Test with event dispatcher
    custom_gateway.events.set_dispatcher(Mock(spec=EventDispatcher))
    metadata_with_events = custom_gateway.get_gateway_status()
    assert metadata_with_events["events"]["enabled"] is True


def test_base_gateway_event_handler_registration(mock_event_dispatcher):
    """BaseGateway supports event handler registration via events capability."""
    gateway = ConcreteGateway()
    gateway.events.set_dispatcher(mock_event_dispatcher)

    # Test decorator usage and direct registration
    decorator = gateway.events.register_handler("test_event")
    assert callable(decorator)

    def test_handler(event):
        return "handled"

    result = gateway.events.register_handler("direct_event", test_handler)
    assert result == gateway.events  # Method chaining returns EventCapability

    # Test error when no dispatcher set
    no_dispatcher_gateway = ConcreteGateway()
    with pytest.raises(ValueError, match="Event dispatcher not set"):
        no_dispatcher_gateway.events.register_handler("event", test_handler)


def test_protocol_handler_capabilities_and_factory_method():
    """BaseProtocolHandler provides capabilities introspection and factory method."""
    # Test capabilities
    handler = ConcreteProtocolHandler()
    handler.register_handler("op1", lambda: "result1")
    handler.register_handler("op2", lambda: "result2")

    capabilities = handler.get_capabilities()
    assert set(capabilities) == {"op1", "op2"}

    # Test factory method
    factory_handler = ConcreteProtocolHandler.create(
        config=GatewayConfig(system_type="FACTORY_TEST"), return_errors=True
    )

    assert isinstance(factory_handler, ConcreteProtocolHandler)
    assert factory_handler.config.system_type == "FACTORY_TEST"
    assert factory_handler.return_errors is True
