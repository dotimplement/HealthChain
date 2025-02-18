"""Helper functions for working with FHIR Bundles.

Example usage:
    >>> from healthchain.fhir import create_bundle, get_resources, set_resources
    >>>
    >>> # Create a bundle
    >>> bundle = create_bundle()
    >>>
    >>> # Add and retrieve conditions
    >>> conditions = get_resources(bundle, "Condition")
    >>> set_resources(bundle, [new_condition], "Condition")
    >>>
    >>> # Add and retrieve medications
    >>> medications = get_resources(bundle, "MedicationStatement")
    >>> set_resources(bundle, [new_medication], "MedicationStatement")
    >>>
    >>> # Add and retrieve allergies
    >>> allergies = get_resources(bundle, "AllergyIntolerance")
    >>> set_resources(bundle, [new_allergy], "AllergyIntolerance")
"""

from typing import List, Type, TypeVar, Optional, Union
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.resource import Resource


T = TypeVar("T", bound=Resource)


def create_bundle(bundle_type: str = "collection") -> Bundle:
    """Create an empty FHIR Bundle.
    https://www.hl7.org/fhir/bundle.html

    Args:
        bundle_type: The type of bundle (default: collection)
            Valid types: document, message, transaction, transaction-response,
            batch, batch-response, history, searchset, collection
    """
    return Bundle(type=bundle_type, entry=[])


def add_resource(
    bundle: Bundle, resource: Resource, full_url: Optional[str] = None
) -> None:
    """Add a resource to a bundle.

    Args:
        bundle: The bundle to add to
        resource: The resource to add, e.g. Condition, MedicationStatement, AllergyIntolerance
        full_url: Optional full URL for the resource
    """
    entry = BundleEntry(resource=resource)
    if full_url:
        entry.fullUrl = full_url
    bundle.entry = (bundle.entry or []) + [entry]


def get_resource_type(resource_type: Union[str, Type[Resource]]) -> Type[Resource]:
    """Get the resource type class from string or type.

    Args:
        resource_type: String name of the resource type (e.g. "Condition") or the type itself

    Returns:
        The resource type class

    Raises:
        ValueError: If the resource type is not supported or cannot be imported
    """
    if isinstance(resource_type, type) and issubclass(resource_type, Resource):
        return resource_type

    if not isinstance(resource_type, str):
        raise ValueError(
            f"Resource type must be a string or Resource class, got {type(resource_type)}"
        )

    try:
        # Try to import the resource type dynamically from fhir.resources
        module = __import__(
            f"fhir.resources.{resource_type.lower()}", fromlist=[resource_type]
        )
        return getattr(module, resource_type)
    except (ImportError, AttributeError) as e:
        raise ValueError(
            f"Could not import resource type: {resource_type}. "
            "Make sure it is a valid FHIR resource type."
        ) from e


def get_resources(
    bundle: Bundle, resource_type: Union[str, Type[Resource]]
) -> List[Resource]:
    """Get all resources of a specific type from a bundle.

    Args:
        bundle: The bundle to search
        resource_type: String name of the resource type (e.g. "Condition") or the type itself

    Returns:
        List of resources of the specified type

    Example:
        >>> bundle = create_bundle()
        >>> # Using string identifier
        >>> conditions = get_resources(bundle, "Condition")
        >>> medications = get_resources(bundle, "MedicationStatement")
        >>> allergies = get_resources(bundle, "AllergyIntolerance")
        >>>
        >>> # Or using type directly
        >>> from fhir.resources.condition import Condition
        >>> conditions = get_resources(bundle, Condition)
    """
    type_class = get_resource_type(resource_type)
    return [
        entry.resource
        for entry in (bundle.entry or [])
        if isinstance(entry.resource, type_class)
    ]


def set_resources(
    bundle: Bundle,
    resources: List[Resource],
    resource_type: Union[str, Type[Resource]],
    replace: bool = True,
) -> None:
    """Set resources of a specific type in the bundle.

    Args:
        bundle: The bundle to modify
        resources: The new resources to add
        resource_type: String name of the resource type (e.g. "Condition") or the type itself
        replace: If True, remove existing resources of this type before adding new ones.
                If False, append new resources to existing ones. Defaults to True.

    Example:
        >>> bundle = create_bundle()
        >>> # Append to existing resources (default behavior)
        >>> set_resources(bundle, [condition1, condition2], "Condition")
        >>> set_resources(bundle, [medication1], "MedicationStatement")
        >>>
        >>> # Replace existing resources
        >>> set_resources(bundle, [condition3], "Condition", replace=True)
        >>>
        >>> # Or using type directly
        >>> from fhir.resources.condition import Condition
        >>> set_resources(bundle, [condition1, condition2], Condition)
    """
    type_class = get_resource_type(resource_type)

    # Remove existing resources of this type if replace=True
    if replace:
        bundle.entry = [
            entry
            for entry in (bundle.entry or [])
            if not isinstance(entry.resource, type_class)
        ]

    # Add new resources
    for resource in resources:
        if not isinstance(resource, type_class):
            raise ValueError(
                f"Resource must be of type {type_class.__name__}, "
                f"got {type(resource).__name__}"
            )
        add_resource(bundle, resource)
