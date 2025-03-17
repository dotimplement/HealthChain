import logging
import importlib
from typing import Dict, List, Optional, Union

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle

log = logging.getLogger(__name__)


def create_resource(resource_dict: Dict, resource_type: str) -> Optional[Resource]:
    """Create a FHIR resource instance from a dictionary

    Args:
        resource_dict: Dictionary representation of the resource
        resource_type: Type of FHIR resource to create

    Returns:
        Optional[Resource]: FHIR resource instance or None if creation failed
    """
    try:
        resource_module = importlib.import_module(
            f"fhir.resources.{resource_type.lower()}"
        )
        resource_class = getattr(resource_module, resource_type)
        return resource_class(**resource_dict)
    except Exception as e:
        log.error(f"Failed to create FHIR resource: {str(e)}")
        return None


def normalize_resource_list(
    resources: Union[Resource, List[Resource], Bundle],
) -> List[Resource]:
    """Convert input resources to a normalized list format

    Args:
        resources: A FHIR Bundle, list of resources, or single resource

    Returns:
        List of FHIR resources
    """
    if isinstance(resources, Bundle):
        return [entry.resource for entry in resources.entry if entry.resource]
    elif isinstance(resources, list):
        return resources
    else:
        return [resources]


def find_section_key_for_resource_type(
    resource_type: str, section_configs: Dict
) -> Optional[str]:
    """Find the appropriate section key for a given resource type

    Args:
        resource_type: FHIR resource type
        config_manager: Configuration manager instance

    Returns:
        Section key or None if no matching section found
    """
    # Find matching section for resource type
    section_key = next(
        (
            key
            for key, config in section_configs.items()
            if config.get("resource") == resource_type
        ),
        None,
    )

    if not section_key:
        log.warning(f"Unsupported resource type: {resource_type}")

    return section_key
