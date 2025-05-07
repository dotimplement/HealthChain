from typing import Dict, Any
from pydantic import BaseModel, field_validator
from fhir.resources.resource import Resource
from fhir.resources import get_fhir_model_class


class Prefetch(BaseModel):
    prefetch: Dict[str, Any]

    @field_validator("prefetch")
    @classmethod
    def validate_fhir_resources(cls, v: Dict[str, Any]) -> Dict[str, Resource]:
        if not v:
            return v

        validated = {}
        for key, resource_dict in v.items():
            if not isinstance(resource_dict, dict):
                continue

            resource_type = resource_dict.get("resourceType")
            if not resource_type:
                continue

            try:
                # Get the appropriate FHIR resource class
                resource_class = get_fhir_model_class(resource_type)
                # Convert the dict to a FHIR resource
                validated[key] = resource_class.model_validate(resource_dict)
            except Exception as e:
                raise ValueError(f"Failed to validate FHIR resource {key}: {str(e)}")

        return validated
