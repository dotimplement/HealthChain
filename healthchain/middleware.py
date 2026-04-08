import logging
import json
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from healthchain.db.connection import session_scope
from healthchain.db.models.audit import AuditEvent
from healthchain.utils.audit_mapper import map_to_fhir_audit_event
from healthchain.utils.logger import add_handlers


log = add_handlers(logging.getLogger("HealthChain.Audit"))


class FHIRAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-request: Capture the payload for searching
        request_json = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                request_json = json.loads(body)


                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
            except Exception:
                pass

        response = await call_next(request)


        try:

            audit_resource = map_to_fhir_audit_event(request, response, request_json)

            # Write to database using  connection.py session
            with session_scope() as session:
                audit_record = AuditEvent(
                    id=audit_resource.get("id"),
                    users=str(audit_resource.get("agent", [{}])[0].get("who", "Unknown")),
                    accessed_info=request.url.path,
                    action=audit_resource.get("action", "E"),
                    resource=audit_resource
                )
                session.add(audit_record)

            log.info(f"AUDIT LOGGED: {request.method} {request.url.path} SUCCESS")
        except Exception as e:
            log.error(f"AUDIT FAILED: {str(e)}")

        return response