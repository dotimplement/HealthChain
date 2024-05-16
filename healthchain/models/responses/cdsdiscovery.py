"""
https://cds-hooks.org/specification/current/#discovery
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class CDSService(BaseModel):
    """
    A model representing a CDS service configuration.

    Attributes:
        hook (str): The hook this service should be invoked on. This should correspond to one of the predefined hooks.
        title (Optional[str]): The human-friendly name of this service. It is recommended to provide this for better usability.
        description (str): A detailed description of what this service does and its purpose within the CDS framework.
        id (str): The unique identifier of this service. It forms part of the URL as {baseUrl}/cds-services/{id}.
        prefetch (Optional[Dict[str, str]]): Optional FHIR queries that the service requests the CDS Client to perform
                                            and provide on each service call. Keys describe the type of data and values are the actual FHIR query strings.
        usageRequirements (Optional[str]): Human-friendly description of any preconditions for the use of this CDS service.

    Documentation: https://cds-hooks.org/specification/current/#response
    """

    hook: str
    description: str
    id: str
    title: Optional[str] = None
    prefetch: Optional[Dict[str, Any]] = None
    usageRequirements: Optional[str] = None


class CDSServiceInformation(BaseModel):
    """
    A CDS Service is discoverable via a stable endpoint by CDS Clients. The Discovery endpoint includes information such as a
    description of the CDS Service, when it should be invoked, and any data that is requested to be prefetched.
    """

    services: List[CDSService] = []
