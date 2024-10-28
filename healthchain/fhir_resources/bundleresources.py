from pydantic import Field, BaseModel, model_validator
from typing import List, Literal, Any

from healthchain.fhir_resources.resourceregistry import ImplementedResourceRegistry

implemented_resources = [f"{item.value}" for item in ImplementedResourceRegistry]


class BundleEntry(BaseModel):
    resource_field: Any = Field(
        default=None,
        alias="resource",
        description="The Resource for the entry. The purpose/meaning of the resource is determined by the Bundle.type. This is allowed to be a Parameters resource if and only if it is referenced by something else within the Bundle that provides context/meaning.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_and_convert_resource(cls, values):
        """
        Validates and converts the resource field in the BundleEntry.

        This method performs the following tasks:
        1. Checks if the resource is None, in which case it returns the values unchanged.
        2. If the resource is already a Pydantic BaseModel, it verifies that it's an implemented resource type.
        3. If the resource is a dictionary, it checks for the presence of a 'resourceType' key and validates that it's an implemented resource type.
        4. Dynamically imports the appropriate resource class based on the resourceType.
        5. Recursively converts nested dictionaries to the appropriate Pydantic models.

        Args:
            cls: The class on which this method is called.
            values (dict): A dictionary containing the field values of the BundleEntry.

        Returns:
            dict: The validated and potentially modified values dictionary.

        Raises:
            ValueError: If the resource is invalid or of an unsupported type.
        """
        resource = values.get("resource")

        if resource is None:
            return values  # Return unchanged if resource is None

        if isinstance(resource, BaseModel):
            # If it's already a Pydantic model (e.g., Patient), use it directly
            if resource.__class__.__name__ not in implemented_resources:
                raise ValueError(
                    f"Invalid resource type: {resource.__class__.__name__}. Must be one of {implemented_resources}."
                )
            return values

        if not isinstance(resource, dict) or "resourceType" not in resource:
            raise ValueError(
                "Invalid resource: must be a dictionary with a 'resourceType' key or a valid FHIR resource model"
            )

        resource_type = resource["resourceType"]
        if resource_type not in implemented_resources:
            raise ValueError(
                f"Invalid resourceType: {resource_type}. Must be one of {implemented_resources}."
            )

        # Import the appropriate resource class dynamically
        module = __import__("healthchain.fhir_resources", fromlist=[resource_type])
        resource_class = getattr(module, resource_type)

        # Convert the dictionary to the appropriate Pydantic model
        values["resource"] = resource_class(**resource)
        return values


class Bundle(BaseModel):
    resourceType: Literal["Bundle"] = "Bundle"
    entry_field: List[BundleEntry] = Field(
        default_factory=list,
        alias="entry",
        description="An entry in a bundle resource - will either contain a resource or information about a resource (transactions and history only).",
    )
