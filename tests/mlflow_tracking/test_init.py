"""Tests for MLflow module imports and availability checking."""

import pytest
import tempfile


def test_is_mlflow_available_returns_bool():
    """Test is_mlflow_available returns boolean."""
    from healthchain.mlflow_tracking import is_mlflow_available

    result = is_mlflow_available()

    assert isinstance(result, bool)


def test_patient_context_always_importable():
    """Test PatientContext can always be imported."""
    from healthchain.mlflow_tracking import PatientContext

    context = PatientContext()
    assert context.cohort == "unspecified"


def test_healthcare_run_context_always_importable():
    """Test HealthcareRunContext can always be imported."""
    from healthchain.mlflow_tracking import HealthcareRunContext

    context = HealthcareRunContext(model_id="test", version="1.0")
    assert context.model_id == "test"


def test_all_exports_defined():
    """Test that __all__ contains expected exports."""
    import healthchain.mlflow_tracking as mlflow_tracking_module

    expected_exports = [
        "HealthcareRunContext",
        "PatientContext",
        "log_healthcare_context",
        "is_mlflow_available",
    ]

    for export in expected_exports:
        assert export in mlflow_tracking_module.__all__


def test_log_healthcare_context_importable():
    """Test log_healthcare_context can be imported."""
    from healthchain.mlflow_tracking import log_healthcare_context

    assert callable(log_healthcare_context)


def test_log_healthcare_context_requires_active_run():
    """Test log_healthcare_context raises error without active run."""
    pytest.importorskip("mlflow")

    from healthchain.mlflow_tracking import HealthcareRunContext, log_healthcare_context

    context = HealthcareRunContext(model_id="test", version="1.0")

    with pytest.raises(RuntimeError, match="No active MLflow run"):
        log_healthcare_context(context)


def test_log_healthcare_context_success():
    """Test log_healthcare_context logs params and tags to an active MLflow run."""
    mlflow = pytest.importorskip("mlflow")

    from healthchain.mlflow_tracking import (
        HealthcareRunContext,
        PatientContext,
        log_healthcare_context,
    )

    context = HealthcareRunContext(
        model_id="test-model",
        version="1.0.0",
        organization="Test Org",
        purpose="Unit testing",
        data_sources=["mimic-iv"],
        regulatory_tags=["HIPAA"],
        patient_context=PatientContext(cohort="ICU patients", sample_size=500),
        custom_metadata={"threshold": 0.7, "validated": True},
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        mlflow.set_tracking_uri(f"file://{tmp_dir}")
        mlflow.set_experiment("test-experiment")
        with mlflow.start_run():
            logged = log_healthcare_context(context, log_provenance=False)

            run = mlflow.active_run()
            run_data = mlflow.get_run(run.info.run_id).data

    assert logged["healthchain.model_id"] == "test-model"
    assert logged["healthchain.model_version"] == "1.0.0"
    assert logged["healthchain.organization"] == "Test Org"
    assert logged["healthchain.regulatory_tags"] == "HIPAA"
    assert logged["healthchain.data_sources"] == "mimic-iv"
    assert logged["healthchain.patient_cohort"] == "ICU patients"
    assert run_data.params["healthchain.model_id"] == "test-model"
    assert run_data.tags["healthchain.model_id"] == "test-model"
    # Custom metadata tags use str() — bool True becomes "True"
    assert run_data.tags["healthchain.custom.threshold"] == "0.7"
    assert run_data.tags["healthchain.custom.validated"] == "True"


def test_context_models_independent_of_mlflow():
    """Test context models work without mlflow installed."""
    from healthchain.mlflow_tracking.context import HealthcareRunContext, PatientContext

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
