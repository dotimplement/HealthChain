from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any

from ..hooks.basehookcontext import BaseHookContext

# TODO: add docstrings


class FHIRAuthorization(BaseModel):
    access_token: str  # OAuth2 access token
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    subject: str


class CDSRequest(BaseModel):
    """
    A model representing the data structure for a CDS service call, triggered by specific hooks
    within a healthcare application.

    Attributes:
        hook (str): The hook that triggered this CDS Service call. For example, 'patient-view'.
        hookInstance (UUID): A universally unique identifier for this particular hook call.
        fhirServer (HttpUrl): The base URL of the CDS Client's FHIR server. This field is required if `fhirAuthorization` is provided.
        fhirAuthorization (Optional[FhirAuthorization]): Optional authorization details providing a bearer access token for FHIR resources.
        context (Dict[str, Any]): Hook-specific contextual data required by the CDS service.
        prefetch (Optional[Dict[str, Any]]): Optional FHIR data that was prefetched by the CDS Client.

    Documentation: https://cds-hooks.org/specification/current/#http-request_1
    """

    hook: str
    hookInstance: str
    context: BaseHookContext
    fhirServer: Optional[HttpUrl] = None
    fhirAuthorization: Optional[FHIRAuthorization] = (
        None  # TODO: note this is required if fhirserver is given
    )
    prefetch: Optional[Dict[str, Any]] = (
        None  # fhir resource is passed either thru prefetched template of fhir server
    )
    extension: Optional[List[Dict[str, Any]]] = None
