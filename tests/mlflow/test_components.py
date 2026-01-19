"""Tests for MLFlow pipeline components."""

import pytest
from unittest.mock import MagicMock, patch

from healthchain.io.containers import Document


@pytest.fixture
def mock_tracker():
    """Create a mock MLFlowTracker."""
    tracker = MagicMock()
    tracker.get_run_id.return_value = "test-run-id"
    tracker.log_metrics = MagicMock()
    tracker.log_params = MagicMock()
    tracker._experiment_id = "test-exp-id"
    tracker._ensure_initialized = MagicMock()
    tracker._active_run = MagicMock()
    return tracker


@pytest.fixture
def mock_tracker_no_run():
    """Create a mock MLFlowTracker without active run."""
    tracker = MagicMock()
    tracker.get_run_id.return_value = None
    return tracker


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    return Document(data="Patient presents with chest pain and shortness of breath.")


# MLFlowComponent tests


def test_mlflow_component_initialization(mock_tracker):
    """Test MLFlowComponent initialization."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(
        tracker=mock_tracker,
        track_predictions=True,
        track_timing=True,
        prefix="test",
    )

    assert component.tracker is mock_tracker
    assert component.track_predictions is True
    assert component.track_timing is True
    assert component.prefix == "test"
    assert component._call_count == 0


def test_mlflow_component_pass_through(mock_tracker, sample_document):
    """Test MLFlowComponent passes data through unchanged."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(tracker=mock_tracker)

    result = component(sample_document)

    assert result is sample_document
    assert result.data == "Patient presents with chest pain and shortness of breath."


def test_mlflow_component_skips_without_active_run(
    mock_tracker_no_run, sample_document
):
    """Test MLFlowComponent skips logging when no run is active."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(tracker=mock_tracker_no_run)

    result = component(sample_document)

    assert result is sample_document
    mock_tracker_no_run.log_metrics.assert_not_called()


def test_mlflow_component_increments_call_count(mock_tracker, sample_document):
    """Test MLFlowComponent increments call count."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(tracker=mock_tracker)

    component(sample_document)
    assert component._call_count == 1

    component(sample_document)
    assert component._call_count == 2


def test_mlflow_component_logs_metrics(mock_tracker, sample_document):
    """Test MLFlowComponent logs metrics to tracker."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(tracker=mock_tracker, prefix="pipeline")

    component(sample_document)

    mock_tracker.log_metrics.assert_called_once()
    logged_metrics = mock_tracker.log_metrics.call_args[0][0]
    assert "pipeline.call_count" in logged_metrics


def test_mlflow_component_logs_timing(mock_tracker, sample_document):
    """Test MLFlowComponent logs elapsed time."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(tracker=mock_tracker, track_timing=True)

    component(sample_document)

    logged_metrics = mock_tracker.log_metrics.call_args[0][0]
    assert "pipeline.elapsed_seconds" in logged_metrics


def test_mlflow_component_custom_metric_extractors(mock_tracker, sample_document):
    """Test MLFlowComponent with custom metric extractors."""
    from healthchain.mlflow.components import MLFlowComponent

    def word_count_extractor(data):
        return float(len(data.data.split()))

    component = MLFlowComponent(
        tracker=mock_tracker,
        metric_extractors={"word_count": word_count_extractor},
    )

    component(sample_document)

    logged_metrics = mock_tracker.log_metrics.call_args[0][0]
    assert "pipeline.word_count" in logged_metrics
    assert logged_metrics["pipeline.word_count"] == 9.0


def test_mlflow_component_extractor_error_handling(mock_tracker, sample_document):
    """Test MLFlowComponent handles extractor errors gracefully."""
    from healthchain.mlflow.components import MLFlowComponent

    def failing_extractor(data):
        raise ValueError("Extraction failed")

    component = MLFlowComponent(
        tracker=mock_tracker,
        metric_extractors={"failing": failing_extractor},
    )

    # Should not raise, just skip the metric
    result = component(sample_document)

    assert result is sample_document


def test_mlflow_component_reset(mock_tracker, sample_document):
    """Test MLFlowComponent reset method."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(tracker=mock_tracker)

    component(sample_document)
    component(sample_document)
    assert component._call_count == 2

    component.reset()

    assert component._call_count == 0
    assert component._start_time is None


def test_mlflow_component_log_pipeline_params(mock_tracker):
    """Test MLFlowComponent log_pipeline_params method."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(tracker=mock_tracker, prefix="my_pipeline")

    component.log_pipeline_params({"batch_size": 32, "model": "bert"})

    mock_tracker.log_params.assert_called_once()
    logged_params = mock_tracker.log_params.call_args[0][0]
    assert logged_params["my_pipeline.batch_size"] == 32
    assert logged_params["my_pipeline.model"] == "bert"


def test_mlflow_component_log_pipeline_params_no_run(mock_tracker_no_run):
    """Test log_pipeline_params does nothing without active run."""
    from healthchain.mlflow.components import MLFlowComponent

    component = MLFlowComponent(tracker=mock_tracker_no_run)

    component.log_pipeline_params({"key": "value"})

    mock_tracker_no_run.log_params.assert_not_called()


# MLFlowStartRunComponent tests


def test_start_run_component_initialization(mock_tracker):
    """Test MLFlowStartRunComponent initialization."""
    from healthchain.mlflow.components import MLFlowStartRunComponent

    component = MLFlowStartRunComponent(
        tracker=mock_tracker,
        run_name="test-run",
        tags={"key": "value"},
    )

    assert component.tracker is mock_tracker
    assert component.run_name == "test-run"
    assert component.tags == {"key": "value"}
    assert component._run_started is False


def test_start_run_component_starts_run(sample_document):
    """Test MLFlowStartRunComponent starts a run."""
    mock_tracker = MagicMock()
    mock_tracker.get_run_id.return_value = None
    mock_tracker._experiment_id = "exp-123"
    mock_tracker._ensure_initialized = MagicMock()

    mock_mlflow = MagicMock()

    from healthchain.mlflow.components import MLFlowStartRunComponent

    with patch("healthchain.mlflow.tracker._get_mlflow", return_value=mock_mlflow):
        component = MLFlowStartRunComponent(
            tracker=mock_tracker,
            run_name="auto-start-run",
        )

        result = component(sample_document)

    assert result is sample_document
    assert component._run_started is True
    mock_mlflow.start_run.assert_called_once()


def test_start_run_component_skips_if_already_started(mock_tracker, sample_document):
    """Test MLFlowStartRunComponent skips if run already started."""
    from healthchain.mlflow.components import MLFlowStartRunComponent

    component = MLFlowStartRunComponent(tracker=mock_tracker)
    component._run_started = True

    mock_mlflow = MagicMock()
    with patch("healthchain.mlflow.tracker._get_mlflow", return_value=mock_mlflow):
        component(sample_document)

    mock_mlflow.start_run.assert_not_called()


def test_start_run_component_skips_if_run_active(sample_document):
    """Test MLFlowStartRunComponent skips if tracker has active run."""
    mock_tracker = MagicMock()
    mock_tracker.get_run_id.return_value = "existing-run"

    from healthchain.mlflow.components import MLFlowStartRunComponent

    component = MLFlowStartRunComponent(tracker=mock_tracker)

    mock_mlflow = MagicMock()
    with patch("healthchain.mlflow.tracker._get_mlflow", return_value=mock_mlflow):
        component(sample_document)

    mock_mlflow.start_run.assert_not_called()


# MLFlowEndRunComponent tests


def test_end_run_component_initialization(mock_tracker):
    """Test MLFlowEndRunComponent initialization."""
    from healthchain.mlflow.components import MLFlowEndRunComponent

    component = MLFlowEndRunComponent(tracker=mock_tracker)

    assert component.tracker is mock_tracker


def test_end_run_component_ends_run(mock_tracker, sample_document):
    """Test MLFlowEndRunComponent ends active run."""
    from healthchain.mlflow.components import MLFlowEndRunComponent

    mock_mlflow = MagicMock()

    with patch("healthchain.mlflow.tracker._get_mlflow", return_value=mock_mlflow):
        component = MLFlowEndRunComponent(tracker=mock_tracker)
        result = component(sample_document)

    assert result is sample_document
    mock_mlflow.end_run.assert_called_once()
    assert mock_tracker._active_run is None


def test_end_run_component_skips_if_no_run(mock_tracker_no_run, sample_document):
    """Test MLFlowEndRunComponent skips if no active run."""
    from healthchain.mlflow.components import MLFlowEndRunComponent

    mock_mlflow = MagicMock()

    with patch("healthchain.mlflow.tracker._get_mlflow", return_value=mock_mlflow):
        component = MLFlowEndRunComponent(tracker=mock_tracker_no_run)
        component(sample_document)

    mock_mlflow.end_run.assert_not_called()


# Integration-style tests


def test_component_extracts_nlp_metrics(mock_tracker):
    """Test MLFlowComponent extracts NLP-related metrics."""
    from healthchain.mlflow.components import MLFlowComponent

    doc = Document(data="Test")
    doc._nlp._tokens = ["a", "b", "c"]
    doc._nlp._entities = [{"text": "entity1"}, {"text": "entity2"}]

    component = MLFlowComponent(tracker=mock_tracker, track_predictions=True)
    component(doc)

    logged_metrics = mock_tracker.log_metrics.call_args[0][0]
    assert "pipeline.token_count" in logged_metrics
    assert logged_metrics["pipeline.token_count"] == 3.0
    assert "pipeline.entity_count" in logged_metrics
    assert logged_metrics["pipeline.entity_count"] == 2.0


def test_component_extracts_fhir_metrics(mock_tracker):
    """Test MLFlowComponent extracts FHIR-related metrics."""
    from healthchain.mlflow.components import MLFlowComponent
    from healthchain.fhir import create_condition

    doc = Document(data="Test")
    doc.fhir.problem_list = [
        create_condition(subject="Patient/1", code="123", display="Condition 1"),
        create_condition(subject="Patient/1", code="456", display="Condition 2"),
    ]

    component = MLFlowComponent(tracker=mock_tracker, track_predictions=True)
    component(doc)

    logged_metrics = mock_tracker.log_metrics.call_args[0][0]
    assert "pipeline.condition_count" in logged_metrics
    assert logged_metrics["pipeline.condition_count"] == 2.0
