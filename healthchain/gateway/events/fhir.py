"""
FHIR-specific event handling utilities.

This module provides constants and helper functions for creating
and managing FHIR operation events.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from healthchain.gateway.events.dispatcher import EHREvent, EHREventType


# Mapping of FHIR operations to event types
OPERATION_TO_EVENT = {
    "read": EHREventType.FHIR_READ,
    "search": EHREventType.FHIR_SEARCH,
    "create": EHREventType.FHIR_CREATE,
    "update": EHREventType.FHIR_UPDATE,
    "delete": EHREventType.FHIR_DELETE,
}


def create_fhir_event(
    operation: str,
    resource_type: str,
    resource_id: Optional[str],
    resource: Any = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Optional[EHREvent]:
    """
    Create a standardized FHIR event.

    Args:
        operation: The FHIR operation (read, search, create, update, delete)
        resource_type: The FHIR resource type
        resource_id: The resource ID (can be None for operations like search)
        resource: The resource object or data
        extra_payload: Additional payload data

    Returns:
        EHREvent or None if operation is not mapped

    Example:
        event = create_fhir_event(
            "read", "Patient", "123", patient_resource
        )
    """
    # Get the event type from the mapping
    event_type = OPERATION_TO_EVENT.get(operation)
    if not event_type:
        return None

    # Build the base payload
    payload = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "operation": operation,
    }

    # Add the resource data if available
    if resource:
        payload["resource"] = resource

    # Add any extra payload data
    if extra_payload:
        payload.update(extra_payload)

    # Create and return the event
    return EHREvent(
        event_type=event_type,
        source_system="FHIR",
        timestamp=datetime.now(),
        payload=payload,
        metadata={
            "operation": operation,
            "resource_type": resource_type,
        },
    )
