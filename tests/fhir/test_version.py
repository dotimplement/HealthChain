"""Tests for FHIR version management functionality."""

import pytest

from healthchain.fhir.version import (
    FHIRVersion,
    get_fhir_resource,
    get_default_version,
    set_default_version,
    reset_default_version,
    fhir_version_context,
    convert_resource,
    get_resource_version,
    _resolve_version,
)


def test_fhir_version_enum_values():
    """Test FHIRVersion enum has expected values."""
    assert FHIRVersion.STU3 == "STU3"
    assert FHIRVersion.R4B == "R4B"
    assert FHIRVersion.R5 == "R5"


def test_fhir_version_enum_from_string():
    """Test creating FHIRVersion from string."""
    assert FHIRVersion("STU3") == FHIRVersion.STU3
    assert FHIRVersion("R4B") == FHIRVersion.R4B
    assert FHIRVersion("R5") == FHIRVersion.R5


def test_resolve_version_with_none():
    """Test _resolve_version returns default when None."""
    reset_default_version()
    assert _resolve_version(None) == FHIRVersion.R5


def test_resolve_version_with_enum():
    """Test _resolve_version passes through enum."""
    assert _resolve_version(FHIRVersion.R4B) == FHIRVersion.R4B


def test_resolve_version_with_string():
    """Test _resolve_version converts string to enum."""
    assert _resolve_version("R4B") == FHIRVersion.R4B
    assert _resolve_version("r4b") == FHIRVersion.R4B  # case insensitive


def test_resolve_version_invalid_string():
    """Test _resolve_version raises for invalid string."""
    with pytest.raises(ValueError, match="Invalid FHIR version"):
        _resolve_version("invalid")


def test_get_default_version_initial():
    """Test initial default version is R5."""
    reset_default_version()
    assert get_default_version() == FHIRVersion.R5


def test_set_default_version_with_enum():
    """Test setting default version with enum."""
    reset_default_version()
    set_default_version(FHIRVersion.R4B)
    assert get_default_version() == FHIRVersion.R4B
    reset_default_version()


def test_set_default_version_with_string():
    """Test setting default version with string."""
    reset_default_version()
    set_default_version("STU3")
    assert get_default_version() == FHIRVersion.STU3
    reset_default_version()


def test_reset_default_version():
    """Test resetting default version to R5."""
    set_default_version(FHIRVersion.R4B)
    reset_default_version()
    assert get_default_version() == FHIRVersion.R5


def test_get_fhir_resource_r5_default():
    """Test loading resource with default R5 version."""
    reset_default_version()
    Patient = get_fhir_resource("Patient")
    assert Patient.__module__ == "fhir.resources.patient"


def test_get_fhir_resource_r4b():
    """Test loading resource with R4B version."""
    Patient = get_fhir_resource("Patient", "R4B")
    assert Patient.__module__ == "fhir.resources.R4B.patient"


def test_get_fhir_resource_r4b_enum():
    """Test loading resource with R4B enum."""
    Patient = get_fhir_resource("Patient", FHIRVersion.R4B)
    assert Patient.__module__ == "fhir.resources.R4B.patient"


def test_get_fhir_resource_stu3():
    """Test loading resource with STU3 version."""
    Patient = get_fhir_resource("Patient", "STU3")
    assert Patient.__module__ == "fhir.resources.STU3.patient"


def test_get_fhir_resource_multiple_types():
    """Test loading multiple resource types."""
    Condition = get_fhir_resource("Condition", "R4B")
    Bundle = get_fhir_resource("Bundle", "R4B")
    Observation = get_fhir_resource("Observation", "R4B")

    assert Condition.__module__ == "fhir.resources.R4B.condition"
    assert Bundle.__module__ == "fhir.resources.R4B.bundle"
    assert Observation.__module__ == "fhir.resources.R4B.observation"


def test_get_fhir_resource_invalid_type():
    """Test loading invalid resource type raises ValueError."""
    with pytest.raises(ValueError, match="Could not import resource type"):
        get_fhir_resource("InvalidResourceType")


def test_get_fhir_resource_respects_default_version():
    """Test get_fhir_resource uses default version when not specified."""
    reset_default_version()
    set_default_version("R4B")

    Patient = get_fhir_resource("Patient")
    assert Patient.__module__ == "fhir.resources.R4B.patient"

    reset_default_version()


def test_fhir_version_context_basic():
    """Test fhir_version_context changes version temporarily."""
    reset_default_version()
    assert get_default_version() == FHIRVersion.R5

    with fhir_version_context("R4B") as v:
        assert v == FHIRVersion.R4B
        assert get_default_version() == FHIRVersion.R4B
        Patient = get_fhir_resource("Patient")
        assert Patient.__module__ == "fhir.resources.R4B.patient"

    assert get_default_version() == FHIRVersion.R5


def test_fhir_version_context_restores_on_exception():
    """Test fhir_version_context restores version even on exception."""
    reset_default_version()
    assert get_default_version() == FHIRVersion.R5

    with pytest.raises(RuntimeError):
        with fhir_version_context("R4B"):
            assert get_default_version() == FHIRVersion.R4B
            raise RuntimeError("Test exception")

    assert get_default_version() == FHIRVersion.R5


def test_fhir_version_context_nested():
    """Test nested fhir_version_context restores correctly."""
    reset_default_version()

    with fhir_version_context("R4B"):
        assert get_default_version() == FHIRVersion.R4B

        with fhir_version_context("STU3"):
            assert get_default_version() == FHIRVersion.STU3

        assert get_default_version() == FHIRVersion.R4B

    assert get_default_version() == FHIRVersion.R5


def test_convert_resource_r5_to_r4b():
    """Test converting a resource from R5 to R4B."""
    Patient_R5 = get_fhir_resource("Patient", "R5")
    patient_r5 = Patient_R5(id="test-123", gender="male")

    patient_r4b = convert_resource(patient_r5, "R4B")

    assert patient_r4b.__class__.__module__ == "fhir.resources.R4B.patient"
    assert patient_r4b.id == "test-123"
    assert patient_r4b.gender == "male"


def test_convert_resource_r4b_to_r5():
    """Test converting a resource from R4B to R5."""
    Patient_R4B = get_fhir_resource("Patient", "R4B")
    patient_r4b = Patient_R4B(id="test-456", gender="female")

    patient_r5 = convert_resource(patient_r4b, "R5")

    assert patient_r5.__class__.__module__ == "fhir.resources.patient"
    assert patient_r5.id == "test-456"
    assert patient_r5.gender == "female"


def test_convert_resource_with_enum():
    """Test convert_resource accepts FHIRVersion enum."""
    Patient_R5 = get_fhir_resource("Patient", "R5")
    patient = Patient_R5(id="test", gender="other")

    converted = convert_resource(patient, FHIRVersion.R4B)
    assert converted.__class__.__module__ == "fhir.resources.R4B.patient"


def test_get_resource_version_r5():
    """Test detecting version from R5 resource."""
    Patient = get_fhir_resource("Patient", "R5")
    patient = Patient(id="test")

    version = get_resource_version(patient)
    assert version == FHIRVersion.R5


def test_get_resource_version_r4b():
    """Test detecting version from R4B resource."""
    Patient = get_fhir_resource("Patient", "R4B")
    patient = Patient(id="test")

    version = get_resource_version(patient)
    assert version == FHIRVersion.R4B


def test_get_resource_version_stu3():
    """Test detecting version from STU3 resource."""
    Patient = get_fhir_resource("Patient", "STU3")
    patient = Patient(id="test")

    version = get_resource_version(patient)
    assert version == FHIRVersion.STU3


def test_get_resource_version_unknown():
    """Test get_resource_version returns None for non-FHIR objects."""

    class FakeResource:
        pass

    fake = FakeResource()
    version = get_resource_version(fake)
    assert version is None


# Integration tests for versioned resource helpers


def test_create_condition_with_version():
    """Test create_condition with version parameter."""
    from healthchain.fhir import create_condition

    cond_r5 = create_condition("Patient/1", code="123", display="Test")
    cond_r4b = create_condition("Patient/1", code="123", display="Test", version="R4B")

    assert cond_r5.__class__.__module__ == "fhir.resources.condition"
    assert cond_r4b.__class__.__module__ == "fhir.resources.R4B.condition"


def test_create_patient_with_version():
    """Test create_patient with version parameter."""
    from healthchain.fhir import create_patient

    patient_r5 = create_patient(gender="male")
    patient_r4b = create_patient(gender="female", version="R4B")

    assert patient_r5.__class__.__module__ == "fhir.resources.patient"
    assert patient_r4b.__class__.__module__ == "fhir.resources.R4B.patient"


def test_create_observation_with_version():
    """Test create_value_quantity_observation with version parameter."""
    from healthchain.fhir import create_value_quantity_observation

    obs_r5 = create_value_quantity_observation(code="12345", value=98.6, unit="F")
    obs_r4b = create_value_quantity_observation(
        code="12345", value=98.6, unit="F", version="R4B"
    )

    assert obs_r5.__class__.__module__ == "fhir.resources.observation"
    assert obs_r4b.__class__.__module__ == "fhir.resources.R4B.observation"


def test_get_resource_type_with_version():
    """Test get_resource_type with version parameter."""
    from healthchain.fhir import get_resource_type

    Condition_R5 = get_resource_type("Condition")
    Condition_R4B = get_resource_type("Condition", version="R4B")

    assert Condition_R5.__module__ == "fhir.resources.condition"
    assert Condition_R4B.__module__ == "fhir.resources.R4B.condition"


def test_create_single_codeable_concept_with_version():
    """Test create_single_codeable_concept with version parameter."""
    from healthchain.fhir.elementhelpers import create_single_codeable_concept

    cc_r5 = create_single_codeable_concept("123", "Test")
    cc_r4b = create_single_codeable_concept("123", "Test", version="R4B")

    assert cc_r5.__class__.__module__ == "fhir.resources.codeableconcept"
    assert cc_r4b.__class__.__module__ == "fhir.resources.R4B.codeableconcept"
