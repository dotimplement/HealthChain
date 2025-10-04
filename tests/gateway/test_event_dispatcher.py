"""
Tests for the event dispatcher core functionality.

Focuses on pub/sub behavior, handler registration, and event publishing patterns.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from datetime import datetime

from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREvent,
    EHREventType,
)


@pytest.fixture
def mock_fastapi_app():
    """Create a mock FastAPI app for testing."""
    return Mock(spec=FastAPI)


@pytest.fixture
def event_dispatcher():
    """Create an event dispatcher for testing."""
    return EventDispatcher()


@pytest.fixture
def sample_ehr_event():
    """Create a sample EHR event for testing."""
    return EHREvent(
        event_type=EHREventType.FHIR_READ,
        source_system="test_system",
        timestamp=datetime.now(),
        payload={"resource_id": "123", "resource_type": "Patient"},
        metadata={"user": "test_user"},
    )


def test_event_dispatcher_conforms_to_protocol():
    """EventDispatcher implements the required protocol methods."""
    dispatcher = EventDispatcher()

    # Check that dispatcher has all required protocol methods
    assert hasattr(dispatcher, "publish")
    assert hasattr(dispatcher, "init_app")
    assert hasattr(dispatcher, "register_handler")
    assert hasattr(dispatcher, "register_default_handler")
    assert callable(getattr(dispatcher, "publish"))
    assert callable(getattr(dispatcher, "init_app"))


def test_event_dispatcher_initialization():
    """EventDispatcher initializes with empty registry and unique middleware ID."""
    dispatcher = EventDispatcher()

    assert dispatcher.handlers_registry == {}
    assert dispatcher.app is None
    assert isinstance(dispatcher.middleware_id, int)

    # Each instance should have unique middleware ID
    dispatcher2 = EventDispatcher()
    assert dispatcher.middleware_id != dispatcher2.middleware_id


@patch("healthchain.gateway.events.dispatcher.EventHandlerASGIMiddleware")
def test_event_dispatcher_app_initialization(
    mock_middleware, event_dispatcher, mock_fastapi_app
):
    """EventDispatcher correctly initializes with FastAPI app and registers middleware."""
    event_dispatcher.init_app(mock_fastapi_app)

    assert event_dispatcher.app is mock_fastapi_app
    mock_fastapi_app.add_middleware.assert_called_once()

    # Verify middleware was called with correct parameters
    call_args = mock_fastapi_app.add_middleware.call_args
    assert call_args[0][0] == mock_middleware
    assert "handlers" in call_args[1]
    assert call_args[1]["middleware_id"] == event_dispatcher.middleware_id


@pytest.mark.parametrize(
    "event_type,expected_name",
    [
        (EHREventType.FHIR_READ, "fhir.read"),
        (EHREventType.CDS_PATIENT_VIEW, "cds.patient.view"),
        (EHREventType.NOTEREADER_SIGN_NOTE, "notereader.sign.note"),
    ],
)
def test_ehr_event_name_mapping(event_type, expected_name):
    """EHREvent correctly maps event types to string names."""
    event = EHREvent(
        event_type=event_type,
        source_system="test",
        timestamp=datetime.now(),
        payload={},
        metadata={},
    )

    assert event.get_name() == expected_name
    assert event.event_type.value == expected_name


@patch("healthchain.gateway.events.dispatcher.local_handler")
def test_event_handler_registration_returns_decorator(
    mock_local_handler, event_dispatcher
):
    """Event handler registration returns correct fastapi-events decorator."""
    mock_decorator = Mock()
    mock_local_handler.register.return_value = mock_decorator

    result = event_dispatcher.register_handler(EHREventType.FHIR_READ)

    assert result is mock_decorator
    mock_local_handler.register.assert_called_once_with(event_name="fhir.read")


@patch("healthchain.gateway.events.dispatcher.local_handler")
def test_default_handler_registration(mock_local_handler, event_dispatcher):
    """Default handler registration uses wildcard pattern."""
    mock_decorator = Mock()
    mock_local_handler.register.return_value = mock_decorator

    result = event_dispatcher.register_default_handler()

    assert result is mock_decorator
    mock_local_handler.register.assert_called_once_with(event_name="*")


@patch("healthchain.gateway.events.dispatcher.dispatch")
@pytest.mark.asyncio
async def test_event_publishing_with_default_middleware_id(
    mock_dispatch, event_dispatcher, sample_ehr_event
):
    """Event publishing uses dispatcher's middleware ID when none provided."""
    mock_dispatch.return_value = None  # dispatch may return None

    await event_dispatcher.publish(sample_ehr_event)

    mock_dispatch.assert_called_once_with(
        "fhir.read",
        sample_ehr_event.model_dump(exclude_none=True),
        middleware_id=event_dispatcher.middleware_id,
    )


@patch("healthchain.gateway.events.dispatcher.dispatch")
@pytest.mark.asyncio
async def test_event_publishing_with_custom_middleware_id(
    mock_dispatch, event_dispatcher, sample_ehr_event
):
    """Event publishing uses provided middleware ID when specified."""
    custom_middleware_id = 12345
    mock_dispatch.return_value = None

    await event_dispatcher.publish(sample_ehr_event, middleware_id=custom_middleware_id)

    mock_dispatch.assert_called_once_with(
        "fhir.read",
        sample_ehr_event.model_dump(exclude_none=True),
        middleware_id=custom_middleware_id,
    )


@patch("healthchain.gateway.events.dispatcher.dispatch")
@pytest.mark.asyncio
async def test_event_publishing_awaits_dispatch_result(
    mock_dispatch, event_dispatcher, sample_ehr_event
):
    """Event publishing awaits dispatch result when it returns an awaitable."""

    # Create a proper coroutine that can be awaited
    async def mock_coroutine():
        return "dispatched"

    mock_dispatch.return_value = mock_coroutine()

    await event_dispatcher.publish(sample_ehr_event)

    # Verify dispatch was called with correct parameters
    mock_dispatch.assert_called_once_with(
        "fhir.read",
        sample_ehr_event.model_dump(exclude_none=True),
        middleware_id=event_dispatcher.middleware_id,
    )


def test_emit_method_handles_sync_context(event_dispatcher, sample_ehr_event):
    """EventDispatcher.emit creates a new loop when not in async context."""
    # Mock all the asyncio components
    with patch.object(
        event_dispatcher, "publish", new_callable=AsyncMock
    ) as mock_publish:
        with patch(
            "asyncio.get_running_loop", side_effect=RuntimeError("No running loop")
        ):
            with patch("asyncio.new_event_loop") as mock_new_loop:
                mock_loop = Mock()
                mock_new_loop.return_value = mock_loop

                # Call emit from sync context
                event_dispatcher.emit(sample_ehr_event, middleware_id=42)

                # Verify behavior
                mock_new_loop.assert_called_once()
                mock_loop.run_until_complete.assert_called_once()
                mock_loop.close.assert_called_once()
                mock_publish.assert_called_once_with(sample_ehr_event, 42)


def test_emit_method_handles_async_context(event_dispatcher, sample_ehr_event):
    """EventDispatcher.emit correctly handles existing async context."""
    # Mock the async publish method with a regular Mock to avoid coroutine issues
    with patch.object(event_dispatcher, "publish", new_callable=Mock):
        # Test async context - should use create_task
        with patch("asyncio.get_running_loop") as mock_get_loop:
            with patch("asyncio.create_task") as mock_create_task:
                mock_loop = Mock()
                mock_get_loop.return_value = mock_loop

                event_dispatcher.emit(sample_ehr_event)

                # Verify create_task was used (async context)
                mock_create_task.assert_called_once()
                # Check that create_task was called with a coroutine-like object
                call_args = mock_create_task.call_args[0][0]
                assert hasattr(call_args, "__call__")
