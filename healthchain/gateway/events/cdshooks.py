"""
CDS Hooks specific event handling utilities.

This module provides constants and helper functions for creating
and managing CDS Hooks operation events.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from healthchain.gateway.events.dispatcher import EHREvent, EHREventType
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse


# Mapping of CDS Hook types to event types
HOOK_TO_EVENT = {
    "patient-view": EHREventType.CDS_PATIENT_VIEW,
    "encounter-discharge": EHREventType.CDS_ENCOUNTER_DISCHARGE,
    "order-sign": EHREventType.CDS_ORDER_SIGN,
    "order-select": EHREventType.CDS_ORDER_SELECT,
}


def create_cds_hook_event(
    hook_type: str,
    request: CDSRequest,
    response: CDSResponse,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Optional[EHREvent]:
    """
    Create a standardized CDS Hook event.

    Args:
        hook_type: The hook type being invoked (e.g., "patient-view")
        request: The CDSRequest object
        response: The CDSResponse object
        extra_payload: Additional payload data

    Returns:
        EHREvent or None if hook type is not mapped

    Example:
        event = create_cds_hook_event(
            "patient-view", request, response
        )
    """
    # Get the event type from the mapping
    event_type = HOOK_TO_EVENT.get(hook_type, EHREventType.EHR_GENERIC)

    # Build the base payload
    payload = {
        "hook": hook_type,
        "hook_instance": request.hookInstance,
        "context": dict(request.context),
    }

    # Add any extra payload data
    if extra_payload:
        payload.update(extra_payload)

    # Create and return the event
    return EHREvent(
        event_type=event_type,
        source_system="CDS-Hooks",
        timestamp=datetime.now(),
        payload=payload,
        metadata={
            "cards_count": len(response.cards) if response.cards else 0,
        },
    )
