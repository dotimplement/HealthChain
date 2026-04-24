import logging
import asyncio
from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
from fastapi import FastAPI
from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.local import local_handler
from fastapi_events.middleware import EventHandlerASGIMiddleware

from healthchain.execution import (
    RuntimeHooks,
    RuntimeScope,
    RuntimeStatus,
    generate_correlation_id,
    get_correlation_id,
    map_runtime_error,
    record_runtime_event,
    runtime_context,
)

logger = logging.getLogger(__name__)


class EHREventType(Enum):
    EHR_GENERIC = "ehr.generic"
    CDS_PATIENT_VIEW = "cds.patient.view"
    CDS_ENCOUNTER_DISCHARGE = "cds.encounter.discharge"
    CDS_ORDER_SIGN = "cds.order.sign"
    CDS_ORDER_SELECT = "cds.order.select"
    NOTEREADER_SIGN_NOTE = "notereader.sign.note"
    NOTEREADER_PROCESS_NOTE = "notereader.process.note"
    FHIR_READ = "fhir.read"
    FHIR_SEARCH = "fhir.search"
    FHIR_UPDATE = "fhir.update"
    FHIR_DELETE = "fhir.delete"
    FHIR_CREATE = "fhir.create"


class EHREvent(BaseModel):
    event_type: EHREventType
    source_system: str
    timestamp: datetime
    payload: Dict
    metadata: Dict

    def get_name(self) -> str:
        """Return the event name as required by Event protocol."""
        return self.event_type.value


class EventDispatcher:
    """Event dispatcher for handling EHR system events using fastapi-events.

    Provides a simple interface for dispatching healthcare-related events in FastAPI applications.
    Supports both request-scoped and application-scoped event handling.

    Example:
        ```python
        app = FastAPI()
        dispatcher = EventDispatcher()
        dispatcher.init_app(app)

        @dispatcher.register_handler(EHREventType.FHIR_READ)
        async def handle_fhir_read(event):
            event_name, payload = event
            print(f"Processing FHIR read: {payload}")

        event = create_fhir_event(EHREventType.FHIR_READ, "test-system", {"resource_id": "123"})
        await dispatcher.publish(event)
        ```
    """

    def __init__(self, runtime_hooks: Optional[RuntimeHooks] = None):
        """Initialize the event dispatcher."""
        self.handlers_registry = {}
        self.app = None
        self.runtime_hooks = runtime_hooks
        # Generate a unique middleware ID to support dispatching outside of requests
        self.middleware_id = id(self)

    def init_app(self, app: FastAPI):
        """Initialize the dispatcher with a FastAPI app instance.

        Args:
            app (FastAPI): The FastAPI application instance
        """
        self.app = app

        # Register the local handler middleware with our custom middleware ID
        app.add_middleware(
            EventHandlerASGIMiddleware,
            handlers=[local_handler],
            middleware_id=self.middleware_id,
        )

    def register_handler(self, event_type: EHREventType):
        """Helper method that returns a decorator to register event handlers.

        This doesn't actually register the handler, but instead returns the
        correct fastapi-events decorator to use.

        Args:
            event_type (EHREventType): The type of event to handle

        Returns:
            Callable: The decorator from fastapi-events
        """
        # Convert enum to string for fastapi-events
        event_name = event_type.value

        # Return the local_handler.register decorator directly
        return local_handler.register(event_name=event_name)

    def register_default_handler(self):
        """Helper method to register a handler for all events.

        Returns:
            Callable: The decorator from fastapi-events
        """
        # Return the local_handler.register decorator with "*" pattern
        return local_handler.register(event_name="*")

    def set_runtime_hooks(
        self, runtime_hooks: Optional[RuntimeHooks]
    ) -> "EventDispatcher":
        """Attach pluggable runtime hooks for structured interop events."""
        self.runtime_hooks = runtime_hooks
        return self

    async def publish(self, event: EHREvent, middleware_id: Optional[int] = None):
        """Publish an event to all registered handlers.

        Args:
            event (EHREvent): The event to publish
            middleware_id (Optional[int]): Custom middleware ID, defaults to self.middleware_id
                if not provided. This is needed for dispatching outside of request contexts.
        """
        correlation_id = get_correlation_id() or generate_correlation_id()
        event.metadata.setdefault("correlation_id", correlation_id)
        event_name = event.event_type.value
        event_data = event.model_dump(exclude_none=True)

        # Use the provided middleware_id or fall back to the class's middleware_id
        mid = middleware_id or self.middleware_id

        details = {
            "event_type": event_name,
            "source_system": event.source_system,
            "middleware_id": mid,
            "payload_keys": sorted(event.payload.keys()),
            "metadata_keys": sorted(event.metadata.keys()),
        }

        with runtime_context(correlation_id=correlation_id, hooks=self.runtime_hooks):
            record_runtime_event(
                name="interop.event.started",
                activity=RuntimeScope.INTEROP,
                status=RuntimeStatus.STARTED,
                scope=event_name,
                details=details,
                hooks=self.runtime_hooks,
            )

            # Dispatch the event with the middleware_id
            # Note: dispatch may return None instead of an awaitable, so handle that case
            logger.debug(f"Dispatching event: {event_name}")
            try:
                result = dispatch(event_name, event_data, middleware_id=mid)
                if result is not None:
                    await result
            except Exception as exc:
                record_runtime_event(
                    name="interop.event.failed",
                    activity=RuntimeScope.INTEROP,
                    status=RuntimeStatus.FAILED,
                    scope=event_name,
                    details=details,
                    error=map_runtime_error(
                        exc,
                        phase=RuntimeScope.INTEROP,
                        correlation_id=correlation_id,
                    ),
                    hooks=self.runtime_hooks,
                )
                raise

            record_runtime_event(
                name="interop.event.completed",
                activity=RuntimeScope.INTEROP,
                status=RuntimeStatus.COMPLETED,
                scope=event_name,
                details=details,
                hooks=self.runtime_hooks,
            )

    def emit(self, event: EHREvent, middleware_id: Optional[int] = None):
        """Publish an event from synchronous code by handling async context automatically.

        This method handles the complexity of managing event loops when called from
        synchronous contexts, while delegating to the async publish method when
        already in an async context.

        Args:
            event (EHREvent): The event to publish
            middleware_id (Optional[int]): Custom middleware ID, defaults to self.middleware_id
        """
        try:
            # Try to get the running loop (only works in async context)
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, so create_task works
                asyncio.create_task(self.publish(event, middleware_id))
            except RuntimeError:
                # We're not in an async context, create a new loop
                loop = asyncio.new_event_loop()
                try:
                    # Run the coroutine to completion in the new loop
                    loop.run_until_complete(self.publish(event, middleware_id))
                finally:
                    # Clean up the loop
                    loop.close()
        except Exception as e:
            logger.error(f"Failed to publish event: {str(e)}", exc_info=True)
