"""
https://cds-hooks.org/specification/current/#discovery
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class CDSService(BaseModel):
    """
    https://cds-hooks.org/specification/current/#response
    """

    hook: str
    description: str
    id: str
    title: Optional[str]
    prefetch: Optional[Dict[str, Any]] = None
    usageRequirements: Optional[str] = None


class CDSServiceDiscoveryResponse(BaseModel):
    services: List[CDSService]
