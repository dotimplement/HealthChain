"""
Tests for the EventDispatcher in the HealthChain gateway system.

This module tests the functionality of the EventDispatcher class
for handling EHR events in the system.
"""

import pytest
from datetime import datetime
from fastapi import FastAPI

from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREventType,
    EHREvent,
)


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    return FastAPI()


@pytest.fixture
def dispatcher():
    """Create an EventDispatcher for testing."""
    return EventDispatcher()


@pytest.fixture
def initialized_dispatcher(app, dispatcher):
    """Create an EventDispatcher initialized with a FastAPI app."""
    dispatcher.init_app(app)
    return dispatcher


@pytest.fixture
def sample_event():
    """Create a sample EHR event for testing."""
    return EHREvent(
        event_type=EHREventType.EHR_GENERIC,
        source_system="test_system",
        timestamp=datetime.now(),
        payload={"data": "test data"},
        metadata={"test": "metadata"},
    )


def test_event_dispatcher_initialization_and_app_binding(app, dispatcher):
    """EventDispatcher initializes correctly and binds to FastAPI apps."""
    # Test initial state
    assert dispatcher.app is None
    assert dispatcher.middleware_id is not None

    # Test app initialization
    dispatcher.init_app(app)
    assert dispatcher.app == app
    assert len(app.user_middleware) == 1


def test_event_handler_registration_returns_decorator(initialized_dispatcher):
    """EventDispatcher register_handler returns a callable decorator."""
    decorator = initialized_dispatcher.register_handler(EHREventType.EHR_GENERIC)
    assert callable(decorator)


def test_ehr_event_naming_and_types(sample_event):
    """EHREvent provides correct event naming and type validation."""
    assert sample_event.get_name() == "ehr.generic"
    assert EHREventType.EHR_GENERIC.value == "ehr.generic"
    assert EHREventType.FHIR_READ.value == "fhir.read"


# TODO: test async
# @patch("healthchain.gateway.events.dispatcher.dispatch")
# async def test_publish_event(mock_dispatch, initialized_dispatcher, sample_event):
#     """Test that publish correctly dispatches an event."""
#     mock_dispatch.return_value = None
#     await initialized_dispatcher.publish(sample_event)
#     mock_dispatch.assert_called_once()
