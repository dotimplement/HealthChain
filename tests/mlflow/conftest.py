"""Fixtures for MLFlow integration tests."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_mlflow():
    """Mock the mlflow module for testing without actual MLflow installation."""
    mock = MagicMock()

    # Mock experiment
    mock_experiment = MagicMock()
    mock_experiment.experiment_id = "test-exp-123"
    mock_experiment.name = "test-experiment"
    mock_experiment.artifact_location = "/tmp/artifacts"
    mock_experiment.lifecycle_stage = "active"

    # Mock run info
    mock_run_info = MagicMock()
    mock_run_info.run_id = "test-run-456"
    mock_run_info.artifact_uri = "/tmp/artifacts/test-run-456"

    # Mock run
    mock_run = MagicMock()
    mock_run.info = mock_run_info

    # Setup mock behavior
    mock.get_experiment_by_name.return_value = mock_experiment
    mock.create_experiment.return_value = "new-exp-789"
    mock.start_run.return_value = mock_run
    mock.search_experiments.return_value = [mock_experiment]
    mock.search_runs.return_value = MagicMock(to_dict=lambda orient: [])

    return mock


@pytest.fixture
def mock_mlflow_module(mock_mlflow):
    """Patch the mlflow module in the tracker module."""
    with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
        with patch("healthchain.mlflow.tracker._get_mlflow", return_value=mock_mlflow):
            yield mock_mlflow


@pytest.fixture
def mlflow_config():
    """Provides a basic MLFlowConfig for testing."""
    from healthchain.mlflow.config import MLFlowConfig

    return MLFlowConfig(
        tracking_uri="mlruns",
        experiment_name="test-experiment",
        tags={"team": "test-team"},
    )


@pytest.fixture
def mlflow_config_full():
    """Provides an MLFlowConfig with all options set."""
    from healthchain.mlflow.config import MLFlowConfig

    return MLFlowConfig(
        tracking_uri="http://localhost:5000",
        experiment_name="full-test-experiment",
        artifact_location="/custom/artifacts",
        tags={"team": "ml-team", "project": "healthcare"},
        log_system_metrics=True,
        log_models=True,
        registry_uri="http://localhost:5001",
    )


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


@pytest.fixture
def mock_tracker(mock_mlflow_module, mlflow_config):
    """Provides a configured MLFlowTracker with mocked mlflow."""
    from healthchain.mlflow.tracker import MLFlowTracker

    tracker = MLFlowTracker(mlflow_config)
    return tracker


@pytest.fixture
def mock_data_container():
    """Provides a mock DataContainer for component testing."""
    from healthchain.io.containers import Document

    doc = Document(data="Test clinical note with patient information.")
    return doc


@pytest.fixture
def mock_data_container_with_nlp():
    """Provides a mock DataContainer with NLP data."""
    from healthchain.io.containers import Document

    doc = Document(data="Patient presents with hypertension and diabetes.")

    # Mock NLP data
    doc._nlp._tokens = [
        "Patient",
        "presents",
        "with",
        "hypertension",
        "and",
        "diabetes",
    ]
    doc._nlp._entities = [
        {"text": "hypertension", "label": "CONDITION"},
        {"text": "diabetes", "label": "CONDITION"},
    ]

    return doc
