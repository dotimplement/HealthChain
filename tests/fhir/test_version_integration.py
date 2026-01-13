"""Integration tests for FHIR versioning across modules."""

import pytest

from healthchain import set_fhir_version, get_fhir_version
from healthchain.fhir import (
    create_condition,
    create_bundle,
    create_patient,
)
from healthchain.fhir.version import FHIRVersionManager, version_context


@pytest.fixture(autouse=True)
def reset_fhir_version_manager():
    """Reset version before each test."""
    FHIRVersionManager._instance = None
    yield
    FHIRVersionManager._instance = None


# Version integration tests


def test_create_condition_with_different_versions():
    """Test creating conditions with different FHIR versions."""
    # Test with R4B (default)
    set_fhir_version("R4B")
    condition_r4b = create_condition(subject="Patient/123", code="E11.9")
    assert condition_r4b is not None
    assert condition_r4b.id.startswith("hc-")
    assert "R4B" in condition_r4b.__class__.__module__

    # Test with R5
    set_fhir_version("R5")
    condition_r5 = create_condition(subject="Patient/456", code="E11.9")
    assert condition_r5 is not None
    assert condition_r5.id.startswith("hc-")
    # R5 uses default fhir.resources module
    assert condition_r5.__class__.__module__.startswith("fhir.resources")
    assert "R4B" not in condition_r5.__class__.__module__


def test_create_bundle_with_different_versions():
    """Test creating bundles with different FHIR versions."""
    # Test with R4B
    set_fhir_version("R4B")
    bundle_r4b = create_bundle()
    assert bundle_r4b is not None
    assert bundle_r4b.type == "collection"
    assert "R4B" in bundle_r4b.__class__.__module__

    # Test with R5
    set_fhir_version("R5")
    bundle_r5 = create_bundle()
    assert bundle_r5 is not None
    assert bundle_r5.type == "collection"
    assert "R4B" not in bundle_r5.__class__.__module__


def test_create_patient_with_different_versions():
    """Test creating patients with different FHIR versions."""
    # Test with R4
    set_fhir_version("R4")
    patient_r4 = create_patient(gender="male", birth_date="1990-01-01")
    assert patient_r4 is not None
    assert patient_r4.gender == "male"
    assert "R4B" in patient_r4.__class__.__module__

    # Test with R5
    set_fhir_version("R5")
    patient_r5 = create_patient(gender="female", birth_date="1985-05-15")
    assert patient_r5 is not None
    assert patient_r5.gender == "female"
    assert "R4B" not in patient_r5.__class__.__module__


def test_bundle_operations_with_versioned_resources():
    """Test bundle operations work correctly with versioned resources."""
    set_fhir_version("R4B")

    # Create bundle and add resources
    bundle = create_bundle()
    condition = create_condition(subject="Patient/123", code="E11.9")
    patient = create_patient(gender="male", birth_date="1990-01-01")

    # Import bundle helpers
    from healthchain.fhir import add_resource, get_resources

    add_resource(bundle, condition)
    add_resource(bundle, patient)

    # Verify resources were added
    assert len(bundle.entry) == 2

    # Get resources by type
    conditions = get_resources(bundle, "Condition")
    assert len(conditions) == 1
    assert conditions[0].id == condition.id

    patients = get_resources(bundle, "Patient")
    assert len(patients) == 1
    assert patients[0].id == patient.id


def test_version_persistence_across_function_calls():
    """Test that version setting persists across multiple function calls."""
    set_fhir_version("R5")

    # Create multiple resources
    condition1 = create_condition(subject="Patient/1", code="E11.9")
    condition2 = create_condition(subject="Patient/2", code="I10")
    patient = create_patient(gender="male")

    # All should be R5
    assert "R4B" not in condition1.__class__.__module__
    assert "R4B" not in condition2.__class__.__module__
    assert "R4B" not in patient.__class__.__module__


def test_top_level_api_consistency():
    """Test that top-level API and fhir module API are consistent."""
    from healthchain import set_fhir_version as top_set
    from healthchain import get_fhir_version as top_get
    from healthchain.fhir import set_fhir_version as fhir_set
    from healthchain.fhir import get_fhir_version as fhir_get

    # Set via top-level API
    top_set("R5")
    assert top_get() == "R5"
    assert fhir_get() == "R5"

    # Set via fhir module API
    fhir_set("R4")
    assert top_get() == "R4"
    assert fhir_get() == "R4"


def test_create_medication_statement_with_versions():
    """Test creating medication statements with different versions."""
    # Note: This test verifies version switching works. The actual MedicationStatement
    # structure may differ between versions (e.g., medication field structure).
    # We focus on verifying the correct module is loaded for each version.

    set_fhir_version("R4B")
    # R4B uses MedicationStatement with specific field structure
    # For now, we just verify the class comes from the right module
    from healthchain.fhir.version import get_resource_class

    MedicationStatement_R4B = get_resource_class("MedicationStatement")
    assert "R4B" in MedicationStatement_R4B.__module__

    set_fhir_version("R5")
    MedicationStatement_R5 = get_resource_class("MedicationStatement")
    assert "R4B" not in MedicationStatement_R5.__module__

    # Verify they're different classes
    assert MedicationStatement_R4B.__module__ != MedicationStatement_R5.__module__


def test_version_switching_workflow():
    """Test a realistic workflow with version switching."""
    # Start with R4B
    set_fhir_version("R4B")
    assert get_fhir_version() == "R4B"

    # Create some R4B resources
    bundle_r4b = create_bundle()
    patient_r4b = create_patient(gender="male")

    from healthchain.fhir import add_resource

    add_resource(bundle_r4b, patient_r4b)

    # Switch to R5
    set_fhir_version("R5")
    assert get_fhir_version() == "R5"

    # Create R5 resources
    bundle_r5 = create_bundle()
    patient_r5 = create_patient(gender="female")
    add_resource(bundle_r5, patient_r5)

    # Verify both bundles work
    assert len(bundle_r4b.entry) == 1
    assert len(bundle_r5.entry) == 1

    # Verify module paths are different
    assert bundle_r4b.__class__.__module__ != bundle_r5.__class__.__module__


def test_element_helpers_with_versions():
    """Test that element helpers work with different versions."""
    from healthchain.fhir import create_single_codeable_concept

    set_fhir_version("R4B")
    concept_r4b = create_single_codeable_concept(
        code="12345", display="Test Code", system="http://test.com"
    )
    assert concept_r4b is not None
    assert "R4B" in concept_r4b.__class__.__module__

    set_fhir_version("R5")
    concept_r5 = create_single_codeable_concept(
        code="67890", display="Test Code 2", system="http://test.com"
    )
    assert concept_r5 is not None
    assert "R4B" not in concept_r5.__class__.__module__


def test_readers_with_versions():
    """Test that readers work with different versions."""
    from healthchain.fhir import create_resource_from_dict

    set_fhir_version("R4B")
    patient_dict = {
        "resourceType": "Patient",
        "id": "123",
        "gender": "male",
        "birthDate": "1990-01-01",
    }

    patient_r4b = create_resource_from_dict(patient_dict, "Patient")
    assert patient_r4b is not None
    assert patient_r4b.id == "123"
    assert "R4B" in patient_r4b.__class__.__module__

    set_fhir_version("R5")
    patient_r5 = create_resource_from_dict(patient_dict, "Patient")
    assert patient_r5 is not None
    assert patient_r5.id == "123"
    assert "R4B" not in patient_r5.__class__.__module__


# Version context integration tests


def test_version_context_with_resource_creation():
    """Test version context affects resource creation."""
    set_fhir_version("R4B")

    # Create resource in default version
    patient_r4b = create_patient(gender="male")
    assert "R4B" in patient_r4b.__class__.__module__

    # Create resource in different version context
    with version_context("R5"):
        patient_r5 = create_patient(gender="female")
        assert "R4B" not in patient_r5.__class__.__module__

    # After context, should revert to R4B
    patient_r4b_again = create_patient(gender="other")
    assert "R4B" in patient_r4b_again.__class__.__module__


def test_nested_version_contexts():
    """Test nested version contexts work correctly."""
    set_fhir_version("R4")

    _patient_r4 = create_patient(gender="male")

    with version_context("R4B"):
        _patient_r4b = create_patient(gender="female")

        with version_context("R5"):
            patient_r5 = create_patient(gender="other")
            assert "R4B" not in patient_r5.__class__.__module__

        # Back to R4B
        patient_r4b_again = create_patient(gender="unknown")
        assert "R4B" in patient_r4b_again.__class__.__module__

    # Back to R4
    patient_r4_again = create_patient(gender="male")
    assert "R4B" in patient_r4_again.__class__.__module__
