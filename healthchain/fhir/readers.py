"""FHIR conversion and reading functions.

This module provides functions for converting between different FHIR representations
and reading data from FHIR resources.
"""

import logging

from typing import TYPE_CHECKING, Optional, Dict, Any, List

# Import version manager for lazy resource loading
from healthchain.fhir.version import get_resource_class

# Type hints using string annotations (lazy evaluation)
if TYPE_CHECKING:
    from fhir.resources.resource import Resource
    from fhir.resources.documentreference import DocumentReference

logger = logging.getLogger(__name__)


def create_resource_from_dict(
    resource_dict: Dict, resource_type: str
) -> Optional["Resource"]:
    """Create a FHIR resource instance from a dictionary

    Args:
        resource_dict: Dictionary representation of the resource
        resource_type: Type of FHIR resource to create

    Returns:
        Optional[Resource]: FHIR resource instance or None if creation failed
    """
    try:
        from healthchain.fhir.version import get_resource_class

        resource_class = get_resource_class(resource_type)
        return resource_class(**resource_dict)
    except Exception as e:
        logger.error(f"Failed to create FHIR resource: {str(e)}")
        return None


def prefetch_to_bundle(prefetch: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten CDS Hooks prefetch into a collection Bundle dict.

    Converts the keyed prefetch format (used in CDS Hooks) into a flat bundle
    suitable for Dataset.from_fhir_bundle().

    Args:
        prefetch: CDS Hooks prefetch dict with format:
            {"patient": {...}, "observations": {"entry": [...]}, ...}

    Returns:
        Bundle dict with type "collection" and flattened entries

    Example:
        >>> prefetch = request.prefetch
        >>> bundle = prefetch_to_bundle(prefetch)
        >>> dataset = Dataset.from_fhir_bundle(bundle, schema=schema)
    """
    entries = []
    for key, value in prefetch.items():
        if isinstance(value, dict):
            if "entry" in value:  # Searchset bundle
                entries.extend(value["entry"])
            elif "resourceType" in value:  # Single resource
                entries.append({"resource": value})
    return {"type": "collection", "entry": entries}


def convert_prefetch_to_fhir_objects(
    prefetch_dict: Dict[str, Any],
) -> Dict[str, "Resource"]:
    """Convert a dictionary of FHIR resource dicts to FHIR Resource objects.

    Takes a prefetch dictionary where values may be either dict representations of FHIR
    resources or already instantiated FHIR Resource objects, and ensures all values are
    FHIR Resource objects.

    Args:
        prefetch_dict: Dictionary mapping keys to FHIR resource dicts or objects

    Returns:
        Dict[str, Resource]: Dictionary with same keys but all values as FHIR Resource objects

    Example:
        >>> prefetch = {
        ...     "patient": {"resourceType": "Patient", "id": "123"},
        ...     "condition": Condition(id="456", ...)
        ... }
        >>> fhir_objects = convert_prefetch_to_fhir_objects(prefetch)
        >>> isinstance(fhir_objects["patient"], Patient)  # True
        >>> isinstance(fhir_objects["condition"], Condition)  # True
    """

    result: Dict[str, Resource] = {}

    for key, resource_data in prefetch_dict.items():
        if isinstance(resource_data, dict):
            # Convert dict to FHIR Resource object
            resource_type = resource_data.get("resourceType")
            if resource_type:
                try:
                    resource_class = get_resource_class(resource_type)
                    result[key] = resource_class(**resource_data)
                except Exception as e:
                    logger.warning(
                        f"Failed to convert {resource_type} to FHIR object: {e}"
                    )
                    result[key] = resource_data
            else:
                logger.warning(
                    f"No resourceType found for key '{key}', keeping as dict"
                )
                result[key] = resource_data
        elif isinstance(resource_data, Resource):
            # Already a FHIR object
            result[key] = resource_data
        else:
            logger.warning(f"Unexpected type for key '{key}': {type(resource_data)}")
            result[key] = resource_data

    return result


def read_content_attachment(
    document_reference: "DocumentReference",
    include_data: bool = True,
) -> Optional[List[Dict[str, Any]]]:
    """Read the attachments in a human readable format from a FHIR DocumentReference content field.

    Args:
        document_reference: The FHIR DocumentReference resource
        include_data: Whether to include the data of the attachments. If true, the data will be also be decoded (default: True)

    Returns:
        Optional[List[Dict[str, Any]]]: List of dictionaries containing attachment data and metadata,
            or None if no attachments are found:
            [
                {
                    "data": str,
                    "metadata": Dict[str, Any]
                }
            ]
    """
    if not document_reference.content:
        return None

    attachments = []
    for content in document_reference.content:
        attachment = content.attachment
        result = {}

        if include_data:
            result["data"] = (
                attachment.url if attachment.url else attachment.data.decode("utf-8")
            )

        result["metadata"] = {
            "content_type": attachment.contentType,
            "title": attachment.title,
            "creation": attachment.creation,
        }

        attachments.append(result)

    return attachments
