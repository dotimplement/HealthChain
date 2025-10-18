"""Integration tests for HealthChain event system."""

import pytest
from datetime import datetime

from healthchain.gateway import HealthChainAPI, EHREvent, EHREventType
from healthchain.models.requests.cdsrequest import CDSRequest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_event_dispatcher_emit_and_publish(event_dispatcher):
    """EventDispatcher handles both synchronous emit and async publish operations."""
    event = EHREvent(
        event_type=EHREventType.EHR_GENERIC,
        source_system="test",
        timestamp=datetime.now(),
        payload={"data": "test"},
        metadata={},
    )

    # Both operations should complete without error
    event_dispatcher.emit(event)
    await event_dispatcher.publish(event)


@pytest.mark.parametrize(
    "service_fixture,operation,request_fixture",
    [
        ("note_service_with_events", "ProcessDocument", "test_cda_request"),
        ("cds_service_with_events", "encounter-discharge", None),
    ],
)
def test_services_propagate_event_dispatcher(
    service_fixture, operation, request_fixture, request, event_dispatcher
):
    """Services with events enabled correctly propagate the event dispatcher."""
    service = request.getfixturevalue(service_fixture)

    # Verify event capability is configured
    assert service.use_events is True
    assert service.events.dispatcher == event_dispatcher

    # Process a request to ensure event system is engaged
    if request_fixture:
        req = request.getfixturevalue(request_fixture)
        service.handle(operation, request=req)
    else:
        cds_request = CDSRequest(
            hook=operation,
            hookInstance="test",
            context={"patientId": "123", "userId": "Practitioner/1"},
        )
        service.handle(operation, request=cds_request)


def test_healthchain_api_propagates_dispatcher_to_services():
    """HealthChainAPI propagates event dispatcher when registering services with events enabled."""
    app = HealthChainAPI(enable_events=True)
    assert app.event_dispatcher is not None

    # Create and register service with events
    from healthchain.gateway import NoteReaderService

    service = NoteReaderService()

    @service.method("ProcessDocument")
    def process_document(cda_request):
        return cda_request

    app.register_service(service, use_events=True)

    # Service should receive the app's dispatcher
    assert service.events.dispatcher == app.event_dispatcher


def test_custom_event_creator_integration(note_service_with_events):
    """Services support custom event creators for specialized event generation."""

    def custom_creator(operation, request, response):
        return EHREvent(
            event_type=EHREventType.NOTEREADER_PROCESS_NOTE,
            source_system="custom",
            timestamp=datetime.now(),
            payload={"operation": operation},
            metadata={"custom": True},
        )

    note_service_with_events.events.set_event_creator(custom_creator)
    assert note_service_with_events.events._event_creator == custom_creator


def test_event_model_structure_and_naming():
    """EHREvent provides consistent structure and naming convention."""
    event = EHREvent(
        event_type=EHREventType.EHR_GENERIC,
        source_system="test-system",
        timestamp=datetime.now(),
        payload={"data": {"key": "value"}},
        metadata={"env": "test"},
    )

    assert event.event_type == EHREventType.EHR_GENERIC
    assert event.source_system == "test-system"
    assert event.payload["data"]["key"] == "value"
    assert event.metadata["env"] == "test"
    assert event.get_name() == EHREventType.EHR_GENERIC.value
