"""Tests for PatientContext and HealthcareRunContext."""

import datetime
import pytest
from pydantic import ValidationError

from healthchain.mlflow.context import PatientContext, HealthcareRunContext


# PatientContext tests


def test_patient_context_default_values():
    """Test PatientContext with default values."""
    context = PatientContext()

    assert context.cohort == "unspecified"
    assert context.age_range is None
    assert context.sample_size is None
    assert context.inclusion_criteria == []
    assert context.exclusion_criteria == []


def test_patient_context_custom_values():
    """Test PatientContext with custom values."""
    context = PatientContext(
        cohort="ICU patients",
        age_range="18-65",
        sample_size=500,
        inclusion_criteria=["admitted to ICU", "mechanically ventilated"],
        exclusion_criteria=["DNR orders", "palliative care"],
    )

    assert context.cohort == "ICU patients"
    assert context.age_range == "18-65"
    assert context.sample_size == 500
    assert context.inclusion_criteria == ["admitted to ICU", "mechanically ventilated"]
    assert context.exclusion_criteria == ["DNR orders", "palliative care"]


def test_patient_context_model_dump():
    """Test PatientContext serialization."""
    context = PatientContext(
        cohort="test-cohort",
        age_range="30-50",
        sample_size=100,
    )

    data = context.model_dump()

    assert data["cohort"] == "test-cohort"
    assert data["age_range"] == "30-50"
    assert data["sample_size"] == 100


# HealthcareRunContext tests


def test_healthcare_context_required_fields():
    """Test that model_id and version are required."""
    with pytest.raises(ValidationError):
        HealthcareRunContext()

    with pytest.raises(ValidationError):
        HealthcareRunContext(model_id="test")

    with pytest.raises(ValidationError):
        HealthcareRunContext(version="1.0")


def test_healthcare_context_minimal():
    """Test HealthcareRunContext with minimal required fields."""
    context = HealthcareRunContext(model_id="my-model", version="1.0.0")

    assert context.model_id == "my-model"
    assert context.version == "1.0.0"
    assert context.patient_context is None
    assert context.organization is None
    assert context.purpose is None
    assert context.data_sources == []
    assert context.regulatory_tags == []
    assert context.custom_metadata == {}


def test_healthcare_context_full(patient_context):
    """Test HealthcareRunContext with all fields."""
    context = HealthcareRunContext(
        model_id="sepsis-predictor",
        version="2.1.0",
        patient_context=patient_context,
        organization="Test Hospital",
        purpose="Early sepsis detection",
        data_sources=["MIMIC-IV", "eICU"],
        regulatory_tags=["HIPAA", "FDA"],
        custom_metadata={"validated": True, "threshold": 0.7},
    )

    assert context.model_id == "sepsis-predictor"
    assert context.version == "2.1.0"
    assert context.patient_context.cohort == "ICU patients"
    assert context.organization == "Test Hospital"
    assert context.purpose == "Early sepsis detection"
    assert context.data_sources == ["MIMIC-IV", "eICU"]
    assert context.regulatory_tags == ["HIPAA", "FDA"]
    assert context.custom_metadata == {"validated": True, "threshold": 0.7}


def test_healthcare_context_to_dict_minimal():
    """Test to_dict with minimal context."""
    context = HealthcareRunContext(model_id="test-model", version="1.0")

    result = context.to_dict()

    assert result["model_id"] == "test-model"
    assert result["version"] == "1.0"
    assert result["organization"] is None
    assert result["purpose"] is None
    assert result["data_sources"] == []
    assert result["regulatory_tags"] == []
    assert "patient_context" not in result
    assert "custom_metadata" not in result


def test_healthcare_context_to_dict_full(patient_context):
    """Test to_dict with full context."""
    recorded_time = datetime.datetime(
        2024, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc
    )
    context = HealthcareRunContext(
        model_id="test-model",
        version="2.0",
        patient_context=patient_context,
        organization="Hospital",
        purpose="Testing",
        data_sources=["source1"],
        regulatory_tags=["HIPAA"],
        custom_metadata={"key": "value"},
        recorded=recorded_time,
    )

    result = context.to_dict()

    assert result["model_id"] == "test-model"
    assert result["version"] == "2.0"
    assert result["organization"] == "Hospital"
    assert result["purpose"] == "Testing"
    assert result["data_sources"] == ["source1"]
    assert result["regulatory_tags"] == ["HIPAA"]
    assert "patient_context" in result
    assert result["patient_context"]["cohort"] == "ICU patients"
    assert "custom_metadata" in result
    assert result["custom_metadata"]["key"] == "value"
    assert "recorded" in result


def test_healthcare_context_from_model_config():
    """Test from_model_config factory method."""
    context = HealthcareRunContext.from_model_config(
        model_id="factory-model",
        version="3.0",
        organization="Factory Org",
        purpose="Factory test",
    )

    assert context.model_id == "factory-model"
    assert context.version == "3.0"
    assert context.organization == "Factory Org"
    assert context.purpose == "Factory test"
    assert context.recorded is not None


def test_healthcare_context_to_fhir_provenance_raises_validation_error():
    """Test to_fhir_provenance raises error due to missing required fields.

    Note: The current implementation has a bug - FHIR Provenance requires a
    'target' field and doesn't allow reason=None. This test documents the
    current behavior. When fixed, this test should be updated.
    """
    from pydantic import ValidationError

    context = HealthcareRunContext(
        model_id="test-model",
        version="1.0",
        purpose="Testing provenance generation",
    )

    # Current implementation raises ValidationError due to missing 'target'
    # and passing reason=None
    with pytest.raises(ValidationError):
        context.to_fhir_provenance()


def test_healthcare_context_to_fhir_provenance_with_regulatory_tags_raises():
    """Test to_fhir_provenance with regulatory tags still raises due to missing target.

    Note: Even with regulatory tags, the implementation is missing the required
    'target' field for FHIR Provenance.
    """
    from pydantic import ValidationError

    context = HealthcareRunContext(
        model_id="regulated-model",
        version="1.0",
        regulatory_tags=["HIPAA", "FDA-cleared"],
    )

    # Still raises due to missing 'target' field
    with pytest.raises(ValidationError):
        context.to_fhir_provenance()
