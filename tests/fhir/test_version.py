"""Unit tests for FHIR version management."""

import os
import pytest

from healthchain.fhir.version import (
    FHIRVersionManager,
    get_fhir_version,
    set_fhir_version,
    get_resource_class,
    version_context,
    SUPPORTED_VERSIONS,
    DEFAULT_VERSION,
)


@pytest.fixture(autouse=True)
def reset_fhir_version_manager():
    """Reset the singleton instance and environment before each test."""
    FHIRVersionManager._instance = None
    if "HEALTHCHAIN_FHIR_VERSION" in os.environ:
        del os.environ["HEALTHCHAIN_FHIR_VERSION"]
    yield
    # Cleanup after test
    FHIRVersionManager._instance = None
    if "HEALTHCHAIN_FHIR_VERSION" in os.environ:
        del os.environ["HEALTHCHAIN_FHIR_VERSION"]


# FHIRVersionManager tests


def test_singleton_pattern():
    """Test that FHIRVersionManager is a singleton."""
    manager1 = FHIRVersionManager.get_instance()
    manager2 = FHIRVersionManager.get_instance()
    assert manager1 is manager2


def test_default_version():
    """Test that default version is R4B."""
    manager = FHIRVersionManager.get_instance()
    assert manager.get_fhir_version() == DEFAULT_VERSION
    assert DEFAULT_VERSION == "R4B"


def test_set_fhir_version():
    """Test setting FHIR version."""
    manager = FHIRVersionManager.get_instance()

    manager.set_fhir_version("R5")
    assert manager.get_fhir_version() == "R5"

    manager.set_fhir_version("R4")
    assert manager.get_fhir_version() == "R4"

    manager.set_fhir_version("r4b")  # Test case insensitivity
    assert manager.get_fhir_version() == "R4B"


def test_set_invalid_version():
    """Test that setting invalid version raises ValueError."""
    manager = FHIRVersionManager.get_instance()

    with pytest.raises(ValueError, match="Unsupported FHIR version"):
        manager.set_fhir_version("R3")

    with pytest.raises(ValueError, match="Unsupported FHIR version"):
        manager.set_fhir_version("invalid")


def test_version_resolution_stu3():
    """Test version path resolution for STU3."""
    manager = FHIRVersionManager.get_instance()
    path = manager._resolve_version_path("STU3")
    assert path == "fhir.resources.STU3"


def test_version_resolution_r4():
    """Test version path resolution for R4."""
    manager = FHIRVersionManager.get_instance()
    path = manager._resolve_version_path("R4")
    assert path == "fhir.resources.R4B"


def test_version_resolution_r4b():
    """Test version path resolution for R4B."""
    manager = FHIRVersionManager.get_instance()
    path = manager._resolve_version_path("R4B")
    assert path == "fhir.resources.R4B"


def test_version_resolution_r5():
    """Test version path resolution for R5."""
    manager = FHIRVersionManager.get_instance()
    path = manager._resolve_version_path("R5")
    assert path == "fhir.resources"


def test_get_resource_class_from_manager():
    """Test getting resource class."""
    manager = FHIRVersionManager.get_instance()
    manager.set_fhir_version("R4B")

    # Test getting Patient resource
    Patient = manager.get_resource_class("Patient")
    assert Patient is not None
    assert Patient.__name__ == "Patient"

    # Test getting Condition resource
    Condition = manager.get_resource_class("Condition")
    assert Condition is not None
    assert Condition.__name__ == "Condition"


def test_get_resource_class_caching():
    """Test that resource classes are cached."""
    manager = FHIRVersionManager.get_instance()
    manager.set_fhir_version("R4B")

    # First call
    Patient1 = manager.get_resource_class("Patient")

    # Second call should return cached version
    Patient2 = manager.get_resource_class("Patient")

    assert Patient1 is Patient2


def test_get_resource_class_cache_cleared_on_version_change():
    """Test that cache is cleared when version changes."""
    manager = FHIRVersionManager.get_instance()

    # Get Patient class for R4B
    manager.set_fhir_version("R4B")
    Patient_R4B = manager.get_resource_class("Patient")

    # Change version and get Patient class again
    manager.set_fhir_version("R5")
    Patient_R5 = manager.get_resource_class("Patient")

    # They should be different classes from different modules
    assert Patient_R4B.__module__ != Patient_R5.__module__


def test_get_resource_class_invalid_resource():
    """Test that invalid resource type raises ValueError."""
    manager = FHIRVersionManager.get_instance()

    with pytest.raises(ValueError, match="Could not import resource type"):
        manager.get_resource_class("InvalidResource")


def test_version_context_manager():
    """Test version context manager."""
    manager = FHIRVersionManager.get_instance()
    manager.set_fhir_version("R4B")

    assert manager.get_fhir_version() == "R4B"

    # Use context manager to temporarily switch to R5
    with manager.version_context("R5"):
        assert manager.get_fhir_version() == "R5"

    # Version should revert after context
    assert manager.get_fhir_version() == "R4B"


def test_version_context_nesting():
    """Test nested version contexts."""
    manager = FHIRVersionManager.get_instance()
    manager.set_fhir_version("R4")

    with manager.version_context("R4B"):
        assert manager.get_fhir_version() == "R4B"

        with manager.version_context("R5"):
            assert manager.get_fhir_version() == "R5"

        assert manager.get_fhir_version() == "R4B"

    assert manager.get_fhir_version() == "R4"


def test_version_context_invalid_version():
    """Test that version context raises ValueError for invalid version."""
    manager = FHIRVersionManager.get_instance()

    with pytest.raises(ValueError, match="Unsupported FHIR version"):
        with manager.version_context("R3"):
            pass


def test_environment_variable():
    """Test that environment variable sets version."""
    os.environ["HEALTHCHAIN_FHIR_VERSION"] = "R5"
    manager = FHIRVersionManager.get_instance()

    assert manager.get_fhir_version() == "R5"


def test_environment_variable_invalid():
    """Test that invalid environment variable falls back to default."""
    os.environ["HEALTHCHAIN_FHIR_VERSION"] = "invalid"
    manager = FHIRVersionManager.get_instance()

    # Should fall back to default
    assert manager.get_fhir_version() == DEFAULT_VERSION


def test_runtime_override_precedence():
    """Test that runtime override takes precedence over environment variable."""
    os.environ["HEALTHCHAIN_FHIR_VERSION"] = "R4"
    manager = FHIRVersionManager.get_instance()

    # Runtime override should take precedence
    manager.set_fhir_version("R5")
    assert manager.get_fhir_version() == "R5"


def test_config_manager_integration():
    """Test integration with ConfigManager."""
    # This test verifies that ConfigManager integration doesn't crash
    # ConfigManager will be loaded if available, otherwise falls back to default
    manager = FHIRVersionManager.get_instance()

    # Should return a valid version (either from config or default)
    version = manager.get_fhir_version()
    assert version in SUPPORTED_VERSIONS

    # If ConfigManager is loaded and has fhir.version set, it should be used
    # Otherwise, default R4B should be used
    # We can't easily mock this due to dynamic import, so just verify it works
    try:
        from healthchain.config import ConfigManager

        config = ConfigManager.get_instance()
        config_version = config.get_config_value("fhir.version")
        if config_version and config_version.upper() in SUPPORTED_VERSIONS:
            assert version == config_version.upper()
    except Exception:
        # ConfigManager not available or not configured, should use default
        assert version == DEFAULT_VERSION


def test_version_context_with_resource_loading():
    """Test that version context affects resource loading."""
    manager = FHIRVersionManager.get_instance()
    manager.set_fhir_version("R4B")

    # Get Patient class with R4B
    Patient_R4B = manager.get_resource_class("Patient")

    # Use context to temporarily switch to R5
    with manager.version_context("R5"):
        Patient_R5 = manager.get_resource_class("Patient")

        # Different module paths
        assert Patient_R4B.__module__ != Patient_R5.__module__

    # After context, should use R4B again
    Patient_R4B_again = manager.get_resource_class("Patient")
    assert Patient_R4B.__module__ == Patient_R4B_again.__module__


# Module-level function tests


def test_module_get_fhir_version():
    """Test module-level get_fhir_version function."""
    version = get_fhir_version()
    assert version == DEFAULT_VERSION


def test_module_set_fhir_version():
    """Test module-level set_fhir_version function."""
    set_fhir_version("R5")
    assert get_fhir_version() == "R5"


def test_module_get_resource_class():
    """Test module-level get_resource_class function."""
    set_fhir_version("R4B")
    Patient = get_resource_class("Patient")
    assert Patient is not None
    assert Patient.__name__ == "Patient"


def test_module_version_context():
    """Test module-level version_context function."""
    set_fhir_version("R4")

    with version_context("R5"):
        assert get_fhir_version() == "R5"

    assert get_fhir_version() == "R4"


# Supported versions tests


def test_supported_versions():
    """Test that supported versions constant is correct."""
    assert "STU3" in SUPPORTED_VERSIONS
    assert "R4" in SUPPORTED_VERSIONS
    assert "R4B" in SUPPORTED_VERSIONS
    assert "R5" in SUPPORTED_VERSIONS
    assert len(SUPPORTED_VERSIONS) == 4


def test_default_version_in_supported():
    """Test that default version is in supported versions."""
    assert DEFAULT_VERSION in SUPPORTED_VERSIONS
