import copy

from pydantic import BaseModel, Field
from typing import Dict

from healthchain.fhir_resources.bundleresources import Bundle


class CdsFhirData(BaseModel):
    """
    Data model for CDS FHIR data, matching the expected fields in CDSRequests.

    Attributes:
        context (Dict): A dictionary containing contextual information for the CDS request.
        prefetch (Bundle): A Bundle object containing prefetched FHIR resources.

    Methods:
        create(cls, context: Dict, prefetch: Dict): Class method to create a CdsFhirData instance.
        model_dump(*args, **kwargs): Returns a dictionary representation of the model.
        model_dump_json(*args, **kwargs): Returns a JSON string representation of the model.
        model_dump_prefetch(*args, **kwargs): Returns a dictionary representation of the prefetch Bundle.
    """

    context: Dict = Field(default={})
    prefetch: Bundle

    @classmethod
    def create(cls, context: Dict, prefetch: Dict):
        # deep copy to avoid modifying the original prefetch data
        prefetch_copy = copy.deepcopy(prefetch)
        bundle = Bundle(**prefetch_copy)
        return cls(context=context, prefetch=bundle)

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_defaults", False)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("by_alias", True)

        return super().model_dump(*args, **kwargs)

    def model_dump_json(self, *args, **kwargs):
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_defaults", False)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("by_alias", True)

        return super().model_dump_json(*args, **kwargs)

    def model_dump_prefetch(self, *args, **kwargs):
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_defaults", False)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("by_alias", True)

        return self.prefetch.model_dump(*args, **kwargs)
