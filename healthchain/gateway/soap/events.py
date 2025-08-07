"""
NoteReader specific event handling utilities.

This module provides constants and helper functions for creating
and managing NoteReader SOAP operation events.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from healthchain.gateway.events.dispatcher import EHREvent, EHREventType
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse


def create_notereader_event(
    operation: str,
    request: CdaRequest,
    response: CdaResponse,
    system_type: str = "EHR_CDA",
    extra_payload: Optional[Dict[str, Any]] = None,
) -> EHREvent:
    """
    Create a standardized NoteReader event.

    Args:
        operation: The SOAP method name (e.g., "ProcessDocument")
        request: The CdaRequest object
        response: The CdaResponse object
        system_type: The system type identifier
        extra_payload: Additional payload data

    Returns:
        EHREvent for the NoteReader operation

    Example:
        event = create_notereader_event(
            "ProcessDocument", request, response
        )
    """
    # Build the base payload
    payload = {
        "operation": operation,
        "work_type": request.work_type,
        "session_id": request.session_id,
        "has_error": response.error is not None,
    }

    # Add any extra payload data
    if extra_payload:
        payload.update(extra_payload)

    # Create and return the event
    return EHREvent(
        event_type=EHREventType.NOTEREADER_PROCESS_NOTE,
        source_system="NoteReader",
        timestamp=datetime.now(),
        payload=payload,
        metadata={
            "service": "NoteReaderService",
            "system_type": system_type,
        },
    )
