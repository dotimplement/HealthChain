"""
Tests for the EventDispatcher in the HealthChain gateway system.

This module tests the functionality of the EventDispatcher class
for handling EHR events in the system.
"""

import pytest
from datetime import datetime
from fastapi import FastAPI
from unittest.mock import patch

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


def test_event_dispatcher_initialization(dispatcher):
    """Test that EventDispatcher initializes correctly."""
    assert dispatcher.app is None
    assert dispatcher.middleware_id is not None


def test_event_dispatcher_init_app(app, dispatcher):
    """Test that EventDispatcher can be initialized with a FastAPI app."""
    dispatcher.init_app(app)
    assert dispatcher.app == app
    assert len(app.user_middleware) == 1


def test_register_handler(initialized_dispatcher):
    """Test that register_handler returns a decorator."""
    decorator = initialized_dispatcher.register_handler(EHREventType.EHR_GENERIC)
    assert callable(decorator)


# TODO: test async
@patch("healthchain.gateway.events.dispatcher.dispatch")
async def test_publish_event(mock_dispatch, initialized_dispatcher, sample_event):
    """Test that publish correctly dispatches an event."""
    mock_dispatch.return_value = None
    await initialized_dispatcher.publish(sample_event)
    mock_dispatch.assert_called_once()


def test_ehr_event_get_name(sample_event):
    """Test that EHREvent.get_name returns the correct event name."""
    assert sample_event.get_name() == "ehr.generic"


def test_basic_event_types():
    """Test a few basic event types."""
    assert EHREventType.EHR_GENERIC.value == "ehr.generic"
    assert EHREventType.FHIR_READ.value == "fhir.read"
