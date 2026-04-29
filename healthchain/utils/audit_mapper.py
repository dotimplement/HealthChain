from datetime import datetime, timezone
from fastapi import Request, Response

from healthchain.db.models.audit import HTTP_TO_FHIR_ACTION
from healthchain.utils.idgenerator import IdGenerator
from healthchain.utils.utils import search_key_breadth_first


def map_to_fhir_audit_event(request: Request, response: Response, request_json: dict = None) -> dict:
    """
    Maps an HTTP request/response to a FHIR R4B AuditEvent dictionary.
    """
    gen = IdGenerator()

    # extract user identity from request headers
    user_id = "unknown"
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # JWT subject will be decoded in Step 4 — use raw token for now
        user_id = auth_header.split(" ")[1][:20]

    # search for patient or subject reference in request body
    patient_ref = (
        search_key_breadth_first(request_json or {}, "subject")
        or search_key_breadth_first(request_json or {}, "patient")
        or "unknown"
    )

    return {
        "resourceType": "AuditEvent",
        "type": {
            "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
            "code": "rest",
            "display": "RESTful Operation"
        },
        "action": HTTP_TO_FHIR_ACTION.get(request.method, "E"),
        "recorded": datetime.now(timezone.utc).isoformat(),
        "outcome": "0" if response.status_code < 400 else "4",
        "agent": [{
            "requestor": True,
            "who": {
                "reference": f"Practitioner/{user_id}"
            },
            "network": {
                "address": request.client.host if request.client else "unknown",
                "type": "2"
            }
        }],
        "source": {
            "observer": {"display": "HealthChain-Gateway"}
        },
        "entity": [{
            "what": {"reference": f"Patient/{patient_ref}"},
            "description": f"Resource Path: {request.url.path}"
        }]
    }