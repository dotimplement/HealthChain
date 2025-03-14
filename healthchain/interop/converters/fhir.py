"""
FHIR Converter Utilities for HealthChain Interoperability Engine

This module provides utility functions for converting to and from FHIR resources.
"""

import logging
import importlib
import uuid
from typing import Dict, List, Optional, Union, Any

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


def add_required_fields(
    resource_dict: Dict, resource_type: str, config_manager: Any
) -> Dict:
    """Add required fields to resource dictionary based on type

    Args:
        resource_dict: Dictionary representation of the resource
        resource_type: Type of FHIR resource
        config_manager: Configuration manager instance

    Returns:
        Dict: The resource dictionary with required fields added
    """
    # Add common fields
    id_prefix = config_manager.get_config_value("defaults.common.id_prefix", "hc-")
    if "id" not in resource_dict:
        resource_dict["id"] = f"{id_prefix}{str(uuid.uuid4())}"

    # Get default values from configuration if available
    default_subject = config_manager.get_config_value(
        "defaults.common.subject", {"reference": "Patient/example"}
    )
    if "subject" not in resource_dict:
        resource_dict["subject"] = default_subject

    # Add resource-specific required fields
    if resource_type == "Condition":
        if "clinicalStatus" not in resource_dict:
            default_status = config_manager.get_config_value(
                "defaults.resources.Condition.clinicalStatus",
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "unknown",
                        }
                    ]
                },
            )
            resource_dict["clinicalStatus"] = default_status
    elif resource_type == "MedicationStatement":
        if "status" not in resource_dict:
            default_status = config_manager.get_config_value(
                "defaults.resources.MedicationStatement.status", "unknown"
            )
            resource_dict["status"] = default_status
    elif resource_type == "AllergyIntolerance":
        if "clinicalStatus" not in resource_dict:
            default_status = config_manager.get_config_value(
                "defaults.resources.AllergyIntolerance.clinicalStatus",
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                            "code": "unknown",
                        }
                    ]
                },
            )
            resource_dict["clinicalStatus"] = default_status

    return resource_dict


def normalize_resources(
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


def convert_resource_dicts_to_resources(
    resource_dicts: List[Dict], resource_type: str, config_manager: Any
) -> List[Resource]:
    """Convert a list of resource dictionaries to FHIR resources

    Args:
        resource_dicts: List of resource dictionaries
        resource_type: Type of FHIR resource to create
        config_manager: Configuration manager instance

    Returns:
        List of FHIR resources
    """
    resources = []

    for resource_dict in resource_dicts:
        # Add required fields based on resource type
        resource_dict = add_required_fields(
            resource_dict, resource_type, config_manager
        )

        # Create FHIR resource instance
        resource = create_resource(resource_dict, resource_type)
        if resource:
            resources.append(resource)

    return resources


def find_section_for_resource_type(
    resource_type: str, config_manager: Any
) -> Optional[str]:
    """Find the appropriate section key for a given resource type

    Args:
        resource_type: FHIR resource type
        config_manager: Configuration manager instance

    Returns:
        Section key or None if no matching section found
    """
    # Get section configurations
    section_configs = config_manager.get_section_configs()

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
