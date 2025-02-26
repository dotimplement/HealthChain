from typing import Dict
from pydantic import BaseModel
from fhir.resources.resource import Resource


class Prefetch(BaseModel):
    prefetch: Dict[str, Resource]
