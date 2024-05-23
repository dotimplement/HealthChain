from healthchain.fhir_resources.resource_registry import ImplementedResourceRegistry
from pydantic import Field, BaseModel, field_validator
from typing import List, Any

implemented_resources = [f"{item.value}Model" for item in ImplementedResourceRegistry]


class Bundle_EntryModel(BaseModel):
    resource_field: Any = Field(
        default=None,
        alias="resource",
        description="The Resource for the entry. The purpose/meaning of the resource is determined by the Bundle.type. This is allowed to be a Parameters resource if and only if it is referenced by something else within the Bundle that provides context/meaning.",
    )

    @field_validator("resource_field")
    def check_enum(cls, value):
        if value.__class__.__name__ not in implemented_resources:
            raise ValueError(
                f"Invalid value class: {value.__class__.__name__}. Must be one of {implemented_resources}."
            )

        return value


class BundleModel(BaseModel):
    resourceType_field: str = "Bundle"
    entry_field: List[Bundle_EntryModel] = Field(
        default_factory=list,
        alias="entry",
        description="An entry in a bundle resource - will either contain a resource or information about a resource (transactions and history only).",
    )
