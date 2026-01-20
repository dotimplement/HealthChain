"""FHIR version management for multi-version support.

This module provides utilities for working with different FHIR versions (STU3, R4B, R5).
It enables dynamic resource loading, version context management, and basic resource conversion.

Usage:
    from healthchain.fhir.version import get_fhir_resource, FHIRVersion

    # Get a resource class for a specific version
    Patient_R4B = get_fhir_resource("Patient", "R4B")
    Patient_R5 = get_fhir_resource("Patient", FHIRVersion.R5)

    # Set the default version for the session
    set_default_version("R4B")

    # Use context manager for temporary version changes
    with fhir_version_context("STU3"):
        patient = get_fhir_resource("Patient")  # Returns STU3 Patient

    # Convert resources between versions
    patient_r5 = Patient(id="123", gender="male")
    patient_r4b = convert_resource(patient_r5, "R4B")
"""

import importlib
import logging
from contextlib import contextmanager
from enum import Enum
from typing import Any, Generator, Optional, Type, Union

logger = logging.getLogger(__name__)


class FHIRVersion(str, Enum):
    """Supported FHIR versions.

    R5 is the default version in fhir.resources library.
    R4B and STU3 are available via subpackages (e.g., fhir.resources.R4B).
    """

    STU3 = "STU3"
    R4B = "R4B"
    R5 = "R5"


# Module-level default version (None means use R5)
_default_version: Optional[FHIRVersion] = None


def _resolve_version(version: Optional[Union[FHIRVersion, str]]) -> FHIRVersion:
    """Resolve a version parameter to a FHIRVersion enum.

    Args:
        version: Version as enum, string, or None for default

    Returns:
        FHIRVersion enum value

    Raises:
        ValueError: If version string is not a valid FHIR version
    """
    if version is None:
        return get_default_version()

    if isinstance(version, FHIRVersion):
        return version

    try:
        return FHIRVersion(version.upper())
    except ValueError:
        valid_versions = [v.value for v in FHIRVersion]
        raise ValueError(
            f"Invalid FHIR version '{version}'. Must be one of: {valid_versions}"
        )


def get_fhir_resource(
    resource_name: str, version: Optional[Union[FHIRVersion, str]] = None
) -> Type[Any]:
    """Dynamically import a FHIR resource class based on version.

    Args:
        resource_name: Name of the FHIR resource (e.g., "Patient", "Condition")
        version: FHIR version (None for default, or FHIRVersion enum/string)

    Returns:
        The FHIR resource class for the specified version

    Raises:
        ValueError: If version is invalid or resource cannot be imported

    Example:
        >>> Patient_R5 = get_fhir_resource("Patient")
        >>> Patient_R4B = get_fhir_resource("Patient", "R4B")
        >>> Patient_STU3 = get_fhir_resource("Patient", FHIRVersion.STU3)
    """
    resolved_version = _resolve_version(version)

    # Build module path based on version
    # R5 is the default (no subpackage), R4B and STU3 use subpackages
    if resolved_version == FHIRVersion.R5:
        module_path = f"fhir.resources.{resource_name.lower()}"
    else:
        module_path = f"fhir.resources.{resolved_version.value}.{resource_name.lower()}"

    try:
        module = importlib.import_module(module_path)
        resource_class = getattr(module, resource_name)
        logger.debug(f"Loaded {resource_name} from {module_path}")
        return resource_class
    except ImportError as e:
        raise ValueError(
            f"Could not import resource type: {resource_name}. "
            f"Make sure it is a valid FHIR resource type for version '{resolved_version.value}'."
        ) from e
    except AttributeError as e:
        raise ValueError(
            f"Module '{module_path}' does not contain resource '{resource_name}'."
        ) from e


def get_default_version() -> FHIRVersion:
    """Get the current default FHIR version.

    Returns:
        The current default FHIRVersion (R5 if not explicitly set)
    """
    return _default_version or FHIRVersion.R5


def set_default_version(version: Union[FHIRVersion, str]) -> None:
    """Set the global default FHIR version.

    Args:
        version: The FHIR version to use as default

    Example:
        >>> set_default_version("R4B")
        >>> patient = get_fhir_resource("Patient")  # Returns R4B Patient
    """
    global _default_version
    _default_version = _resolve_version(version)
    logger.info(f"Default FHIR version set to {_default_version.value}")


def reset_default_version() -> None:
    """Reset the default FHIR version to library default (R5)."""
    global _default_version
    _default_version = None
    logger.debug("Default FHIR version reset to R5")


@contextmanager
def fhir_version_context(
    version: Union[FHIRVersion, str],
) -> Generator[FHIRVersion, None, None]:
    """Context manager for temporarily changing the default FHIR version.

    Args:
        version: The FHIR version to use within the context

    Yields:
        The resolved FHIRVersion being used

    Example:
        >>> with fhir_version_context("R4B") as v:
        ...     patient = get_fhir_resource("Patient")  # R4B Patient
        ...     print(f"Using {v}")
        >>> # After context, default is restored
    """
    global _default_version
    previous_version = _default_version
    resolved = _resolve_version(version)
    _default_version = resolved
    try:
        yield resolved
    finally:
        _default_version = previous_version


def convert_resource(resource: Any, target_version: Union[FHIRVersion, str]) -> Any:
    """Convert a FHIR resource to a different version.

    Converts by serializing the resource to a dictionary and deserializing
    with the target version's resource class. This approach works for
    resources with compatible field structures.

    Note:
        Field mappings between FHIR versions may not be 1:1. Some fields
        may be added, removed, or renamed between versions. This function
        performs a best-effort conversion and may raise validation errors
        if the resource data is incompatible with the target version.

    Args:
        resource: The FHIR resource to convert
        target_version: The target FHIR version

    Returns:
        A new resource instance of the target version

    Raises:
        ValueError: If the resource type cannot be determined or imported
        ValidationError: If the resource data is incompatible with target version

    Example:
        >>> from fhir.resources.patient import Patient
        >>> patient_r5 = Patient(id="123", gender="male")
        >>> patient_r4b = convert_resource(patient_r5, "R4B")
        >>> print(patient_r4b.__class__.__module__)
        fhir.resources.R4B.patient
    """
    # Get the resource type name from the class
    resource_type = resource.__class__.__name__

    # Get the target version's resource class
    target_class = get_fhir_resource(resource_type, target_version)

    # Serialize to dict and deserialize with target class
    data = resource.model_dump(exclude_none=True)

    logger.debug(
        f"Converting {resource_type} from {resource.__class__.__module__} "
        f"to {target_class.__module__}"
    )

    return target_class.model_validate(data)


def get_resource_version(resource: Any) -> Optional[FHIRVersion]:
    """Detect the FHIR version of a resource based on its module path.

    Args:
        resource: A FHIR resource instance

    Returns:
        The FHIRVersion if detectable, None otherwise

    Example:
        >>> from fhir.resources.R4B.patient import Patient
        >>> patient = Patient(id="123")
        >>> version = get_resource_version(patient)
        >>> print(version)
        FHIRVersion.R4B
    """
    module = resource.__class__.__module__

    if ".R4B." in module:
        return FHIRVersion.R4B
    elif ".STU3." in module:
        return FHIRVersion.STU3
    elif module.startswith("fhir.resources."):
        return FHIRVersion.R5

    return None
