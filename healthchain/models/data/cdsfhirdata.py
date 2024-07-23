from pydantic import BaseModel, Field
from typing import Dict

from healthchain.fhir_resources.bundleresources import Bundle


class CdsFhirData(BaseModel):
    """
    Data model for CDS FHIR data, this matches the expected fields in CDSRequests
    """

    context: Dict = Field(default={})
    prefetch: Bundle

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("by_alias", True)

        return super().model_dump(*args, **kwargs)
