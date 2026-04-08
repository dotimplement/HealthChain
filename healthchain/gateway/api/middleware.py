import logging
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from healthchain.db.connection import session_scope
from healthchain.db.models.audit import AuditEvent
from healthchain.utils.audit_mapper import map_to_fhir_audit_event

log = logging.getLogger("HealthChain.Audit")


class FHIRAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # capture request body before passing on
        request_json = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                import json
                request_json = json.loads(body)

                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
            except Exception:
                pass

        response = await call_next(request)

        try:
            audit_resource = map_to_fhir_audit_event(request, response, request_json)

            with session_scope() as session:
                audit_record = AuditEvent(
                    time=datetime.now(timezone.utc),
                    users=str(
                        audit_resource.get("agent", [{}])[0]
                        .get("who", {})
                        .get("reference", "unknown")
                    ),
                    accessed_info=(
                        audit_resource.get("entity", [{}])[0]
                        .get("what", {})
                        .get("reference", None)
                    ),
                    action=audit_resource.get("action", "E"),
                    resource=audit_resource,
                )
                session.add(audit_record)

            log.info(f"AUDIT LOGGED: {request.method} {request.url.path} → {response.status_code}")
        except Exception as e:
            log.error(f"AUDIT FAILED: {str(e)}")

        return response