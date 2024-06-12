from pydantic import BaseModel, Field
from typing import Dict

from ...fhir_resources.bundle_resources import BundleModel


class GeneratedFhirData(BaseModel):
    context: Dict = Field(default={})
    prefetch: BundleModel
