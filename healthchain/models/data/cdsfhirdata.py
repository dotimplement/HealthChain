from pydantic import BaseModel, Field
from typing import Dict

from healthchain.fhir_resources.bundleresources import Bundle


class CdsFhirData(BaseModel):
    context: Dict = Field(default={})
    prefetch: Bundle

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("by_alias", True)

        return super().model_dump(*args, **kwargs)
