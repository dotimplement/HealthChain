from datetime import datetime, timezone
from fastapi import Request, Response
from healthchain.util.id_generator import IdGenerator
from healthchain.util.search import search_key_breadth_first


def map_to_fhir_audit_event(request: Request, response: Response, request_json: dict = None) -> dict:
    """
    Combines your custom IdGenerator and Search utils to
    create a valid FHIR AuditEvent dictionary.
    """
    gen = IdGenerator()

    # Use your BFS search utility to find a patient ID in the request body
    patient_ref = search_key_breadth_first(request_json or {}, "id") or "unknown-subject"

    return {
        "resourceType": "AuditEvent",
        "id": gen.generate_random_uuid(),  # Using IdGenerator
        "type": {
            "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
            "code": "rest",
            "display": "RESTful Operation"
        },
        "recorded": datetime.now(timezone.utc).isoformat(),
        "outcome": "0" if response.status_code < 400 else "4",
        "agent": [{
            "requestor": True,
            "network": {
                "address": request.client.host if request.client else "127.0.0.1",
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