from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any


class FHIRAuthorization(BaseModel):
    access_token: str  # OAuth2 access token
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    subject: str


class CDSRequest(BaseModel):
    """
    https://cds-hooks.org/specification/current/#http-request_1
    """

    hook: str
    hookInstance: str
    context: Dict[str, Any]
    fhirServer: Optional[HttpUrl] = None
    fhirAuthorization: Optional[FHIRAuthorization] = (
        None  # note this is required if fhirserver is given
    )
    prefetch: Optional[Dict[str, Any]] = (
        None  # fhir resource is passed either thru prefetched template of fhir server
    )
    extension: Optional[List[Dict[str, Any]]] = None
