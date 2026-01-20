"""Tests for MLflow module imports and availability checking."""

import pytest


def test_is_mlflow_available_returns_bool():
    """Test is_mlflow_available returns boolean."""
    from healthchain.mlflow import is_mlflow_available

    result = is_mlflow_available()

    assert isinstance(result, bool)


def test_patient_context_always_importable():
    """Test PatientContext can always be imported."""
    from healthchain.mlflow import PatientContext

    context = PatientContext()
    assert context.cohort == "unspecified"


def test_healthcare_run_context_always_importable():
    """Test HealthcareRunContext can always be imported."""
    from healthchain.mlflow import HealthcareRunContext

    context = HealthcareRunContext(model_id="test", version="1.0")
    assert context.model_id == "test"


def test_all_exports_defined():
    """Test that __all__ contains expected exports."""
    import healthchain.mlflow as mlflow_module

    expected_exports = [
        "HealthcareRunContext",
        "PatientContext",
        "log_healthcare_context",
        "is_mlflow_available",
    ]

    for export in expected_exports:
        assert export in mlflow_module.__all__


def test_log_healthcare_context_importable():
    """Test log_healthcare_context can be imported."""
    from healthchain.mlflow import log_healthcare_context

    assert callable(log_healthcare_context)


def test_log_healthcare_context_requires_active_run():
    """Test log_healthcare_context raises error without active run."""
    pytest.importorskip("mlflow")

    from healthchain.mlflow import HealthcareRunContext, log_healthcare_context

    context = HealthcareRunContext(model_id="test", version="1.0")

    with pytest.raises(RuntimeError, match="No active MLflow run"):
        log_healthcare_context(context)


def test_context_models_independent_of_mlflow():
    """Test context models work without mlflow installed."""
    from healthchain.mlflow.context import HealthcareRunContext, PatientContext

    patient = PatientContext(cohort="test-cohort", sample_size=100)
    assert patient.sample_size == 100

    context = HealthcareRunContext(
        model_id="test-model",
        version="1.0",
        patient_context=patient,
    )
    assert context.patient_context.cohort == "test-cohort"

    # to_dict should work
    data = context.to_dict()
    assert data["model_id"] == "test-model"
