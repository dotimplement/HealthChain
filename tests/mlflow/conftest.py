"""Fixtures for MLflow integration tests."""

import pytest


@pytest.fixture
def patient_context():
    """Provides a PatientContext for testing."""
    from healthchain.mlflow.context import PatientContext

    return PatientContext(
        cohort="ICU patients",
        age_range="18-65",
        sample_size=1000,
        inclusion_criteria=["admitted to ICU", "age >= 18"],
        exclusion_criteria=["DNR orders"],
    )


@pytest.fixture
def healthcare_context(patient_context):
    """Provides a HealthcareRunContext for testing."""
    from healthchain.mlflow.context import HealthcareRunContext

    return HealthcareRunContext(
        model_id="sepsis-predictor",
        version="1.2.0",
        patient_context=patient_context,
        organization="Test Hospital",
        purpose="Early sepsis detection",
        data_sources=["MIMIC-IV", "internal-ehr"],
        regulatory_tags=["HIPAA", "FDA-cleared"],
    )
