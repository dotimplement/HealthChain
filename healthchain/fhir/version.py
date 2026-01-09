"""FHIR version management for HealthChain.

This module provides centralized FHIR version management, allowing users to choose
which FHIR version (STU3, R4, R4B, R5) to use for resource creation and operations.

Usage:
    from healthchain.fhir.version import set_fhir_version, get_fhir_version

    # Set version at startup
    set_fhir_version("R5")

    # Get current version
    version = get_fhir_version()

    # Temporary version context
    with version_context("R4"):
        # Operations here use R4
        pass
"""

import os
import logging
import importlib
from contextlib import contextmanager
from typing import Type, Optional, Dict
from threading import Lock

logger = logging.getLogger(__name__)

# Supported FHIR versions
SUPPORTED_VERSIONS = ["STU3", "R4", "R4B", "R5"]
DEFAULT_VERSION = "R4B"


class FHIRVersionManager:
    """Singleton manager for FHIR version resolution and resource loading.

    This class manages the FHIR version used throughout the HealthChain library,
    providing dynamic resource class loading based on the configured version.

    The version is determined by the following precedence (highest to lowest):
    1. Runtime overrides via set_fhir_version()
    2. Environment variable (HEALTHCHAIN_FHIR_VERSION)
    3. ConfigManager setting (fhir.version)
    4. Default: R4B
    """

    _instance = None
    _lock = Lock()

    def __init__(self):
        """Initialize the version manager.

        Note: Use get_instance() instead of creating instances directly.
        """
        self._version: Optional[str] = None
        self._version_stack = []  # For version_context nesting
        self._resource_cache: Dict[tuple, Type] = {}

    @classmethod
    def get_instance(cls) -> "FHIRVersionManager":
        """Get the singleton instance of FHIRVersionManager.

        Returns:
            The singleton FHIRVersionManager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_fhir_version(self) -> str:
        """Get the current FHIR version.

        Returns the version from the first available source:
        1. Runtime override (set via set_fhir_version)
        2. Environment variable (HEALTHCHAIN_FHIR_VERSION)
        3. ConfigManager (fhir.version)
        4. Default (R4B)

        Returns:
            FHIR version string (e.g., "R4B", "R5")
        """
        # Check version stack first (for version_context)
        if self._version_stack:
            return self._version_stack[-1]

        # Check runtime override
        if self._version is not None:
            return self._version

        # Check environment variable
        env_version = os.environ.get("HEALTHCHAIN_FHIR_VERSION")
        if env_version:
            if env_version.upper() in SUPPORTED_VERSIONS:
                return env_version.upper()
            else:
                logger.warning(
                    f"Invalid FHIR version in HEALTHCHAIN_FHIR_VERSION: {env_version}. "
                    f"Supported versions: {', '.join(SUPPORTED_VERSIONS)}. "
                    f"Falling back to default: {DEFAULT_VERSION}"
                )

        # Check ConfigManager
        try:
            from healthchain.config import ConfigManager

            config = ConfigManager.get_instance()
            config_version = config.get_config_value("fhir.version")
            if config_version:
                if config_version.upper() in SUPPORTED_VERSIONS:
                    return config_version.upper()
                else:
                    logger.warning(
                        f"Invalid FHIR version in config: {config_version}. "
                        f"Supported versions: {', '.join(SUPPORTED_VERSIONS)}. "
                        f"Falling back to default: {DEFAULT_VERSION}"
                    )
        except Exception as e:
            logger.debug(f"Could not load version from ConfigManager: {e}")

        # Return default
        return DEFAULT_VERSION

    def set_fhir_version(self, version: str) -> None:
        """Set the FHIR version to use globally.

        Args:
            version: FHIR version string (STU3, R4, R4B, or R5)

        Raises:
            ValueError: If the version is not supported
        """
        version_upper = version.upper()
        if version_upper not in SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unsupported FHIR version: {version}. "
                f"Supported versions: {', '.join(SUPPORTED_VERSIONS)}"
            )

        self._version = version_upper
        self._resource_cache.clear()  # Clear cache when version changes
        logger.info(f"FHIR version set to: {version_upper}")

    def _resolve_version_path(self, version: str) -> str:
        """Resolve FHIR version string to module path.

        Mapping:
        - STU3 → fhir.resources.STU3
        - R4 → fhir.resources.R4B (R4B is backward compatible)
        - R4B → fhir.resources.R4B
        - R5 → fhir.resources (default package is R5)

        Args:
            version: FHIR version string

        Returns:
            Module path for the version
        """
        version_upper = version.upper()

        if version_upper == "STU3":
            return "fhir.resources.STU3"
        elif version_upper in ["R4", "R4B"]:
            return "fhir.resources.R4B"
        elif version_upper == "R5":
            return "fhir.resources"
        else:
            raise ValueError(
                f"Cannot resolve module path for version: {version}. "
                f"Supported versions: {', '.join(SUPPORTED_VERSIONS)}"
            )

    def get_resource_class(
        self, resource_type: str, version: Optional[str] = None
    ) -> Type:
        """Get a FHIR resource class for the specified version.

        This method dynamically imports the resource class from the appropriate
        fhir.resources module based on the configured version. Results are cached
        for performance.

        Args:
            resource_type: The FHIR resource type name (e.g., "Patient", "Condition")
            version: Optional version override. If not provided, uses get_fhir_version()

        Returns:
            The FHIR resource class

        Raises:
            ValueError: If the resource type cannot be imported

        Example:
            >>> manager = FHIRVersionManager.get_instance()
            >>> Patient = manager.get_resource_class("Patient")
            >>> patient = Patient(id="123")
        """
        if version is None:
            version = self.get_fhir_version()

        # Check cache first
        cache_key = (resource_type, version)
        if cache_key in self._resource_cache:
            return self._resource_cache[cache_key]

        # Resolve version to module path
        base_path = self._resolve_version_path(version)
        module_path = f"{base_path}.{resource_type.lower()}"

        try:
            # Import the module
            module = importlib.import_module(module_path)
            resource_class = getattr(module, resource_type)

            # Cache the result
            self._resource_cache[cache_key] = resource_class

            logger.debug(f"Loaded {resource_type} from {module_path}")
            return resource_class

        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Could not import resource type '{resource_type}' for FHIR version {version}. "
                f"Make sure it is a valid FHIR resource type. Module path: {module_path}"
            ) from e

    @contextmanager
    def version_context(self, version: str):
        """Context manager for temporarily using a different FHIR version.

        This is useful for operations that need to use a specific version
        without changing the global version setting.

        Args:
            version: FHIR version to use within the context

        Yields:
            None

        Example:
            >>> manager = FHIRVersionManager.get_instance()
            >>> with manager.version_context("R4"):
            ...     # Operations here use R4
            ...     patient = create_patient(...)
        """
        version_upper = version.upper()
        if version_upper not in SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unsupported FHIR version: {version}. "
                f"Supported versions: {', '.join(SUPPORTED_VERSIONS)}"
            )

        # Push version onto stack
        self._version_stack.append(version_upper)
        try:
            yield
        finally:
            # Pop version from stack
            self._version_stack.pop()


# Module-level convenience functions

_manager = None


def _get_manager() -> FHIRVersionManager:
    """Get the global version manager instance."""
    global _manager
    if _manager is None:
        _manager = FHIRVersionManager.get_instance()
    return _manager


def get_fhir_version() -> str:
    """Get the current FHIR version.

    Returns:
        FHIR version string (e.g., "R4B", "R5")

    Example:
        >>> from healthchain.fhir.version import get_fhir_version
        >>> version = get_fhir_version()
        >>> print(version)
        'R4B'
    """
    return _get_manager().get_fhir_version()


def set_fhir_version(version: str) -> None:
    """Set the FHIR version to use globally.

    Args:
        version: FHIR version string (STU3, R4, R4B, or R5)

    Raises:
        ValueError: If the version is not supported

    Example:
        >>> from healthchain.fhir.version import set_fhir_version
        >>> set_fhir_version("R5")
    """
    _get_manager().set_fhir_version(version)


def get_resource_class(resource_type: str, version: Optional[str] = None) -> Type:
    """Get a FHIR resource class for the specified version.

    Args:
        resource_type: The FHIR resource type name (e.g., "Patient", "Condition")
        version: Optional version override

    Returns:
        The FHIR resource class

    Raises:
        ValueError: If the resource type cannot be imported

    Example:
        >>> from healthchain.fhir.version import get_resource_class
        >>> Patient = get_resource_class("Patient")
        >>> patient = Patient(id="123")
    """
    return _get_manager().get_resource_class(resource_type, version)


@contextmanager
def version_context(version: str):
    """Context manager for temporarily using a different FHIR version.

    Args:
        version: FHIR version to use within the context

    Yields:
        None

    Example:
        >>> from healthchain.fhir.version import version_context
        >>> with version_context("R4"):
        ...     # Operations here use R4
        ...     patient = create_patient(...)
    """
    with _get_manager().version_context(version):
        yield
