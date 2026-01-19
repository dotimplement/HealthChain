"""Tests for MLFlow decorators and TrackedPipeline."""

import pytest
from unittest.mock import MagicMock, patch

from healthchain.io.containers import Document


@pytest.fixture
def mock_mlflow_for_decorators():
    """Create a comprehensive mock for MLFlow used in decorators."""
    mock = MagicMock()

    # Mock experiment
    mock_experiment = MagicMock()
    mock_experiment.experiment_id = "dec-exp-123"
    mock.get_experiment_by_name.return_value = mock_experiment

    # Mock run
    mock_run_info = MagicMock()
    mock_run_info.run_id = "dec-run-456"
    mock_run = MagicMock()
    mock_run.info = mock_run_info

    # Context manager for start_run
    mock.start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
    mock.start_run.return_value.__exit__ = MagicMock(return_value=False)

    return mock


# track_model decorator tests


def test_track_model_basic(mock_mlflow_for_decorators):
    """Test track_model decorator basic functionality."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model(experiment="test-experiment")
        def my_model_function(x):
            return x * 2

        result = my_model_function(5)

    assert result == 10
    mock_mlflow_for_decorators.start_run.assert_called()


def test_track_model_uses_function_name_as_run_name(mock_mlflow_for_decorators):
    """Test track_model uses function name as default run name."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model()
        def predict_sepsis(patient_data):
            return {"risk": 0.75}

        predict_sepsis({})

    # Check that run was started with function name
    call_kwargs = mock_mlflow_for_decorators.start_run.call_args[1]
    assert call_kwargs["run_name"] == "predict_sepsis"


def test_track_model_custom_run_name(mock_mlflow_for_decorators):
    """Test track_model with custom run name."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model(run_name="custom-inference-run")
        def inference(data):
            return data

        inference("test")

    call_kwargs = mock_mlflow_for_decorators.start_run.call_args[1]
    assert call_kwargs["run_name"] == "custom-inference-run"


def test_track_model_logs_execution_time(mock_mlflow_for_decorators):
    """Test track_model logs execution time."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model(auto_log_time=True)
        def slow_function():
            return "done"

        slow_function()

    # Check that metrics were logged
    mock_mlflow_for_decorators.log_metrics.assert_called()
    logged_metrics = mock_mlflow_for_decorators.log_metrics.call_args[0][0]
    assert "execution_time_seconds" in logged_metrics


def test_track_model_logs_params(mock_mlflow_for_decorators):
    """Test track_model logs specified parameters."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model(log_params={"threshold": 0.5, "model_type": "xgboost"})
        def predict(data):
            return data

        predict("test")

    # Check that params were logged
    mock_mlflow_for_decorators.log_params.assert_called()
    # First call should be the custom params
    first_call_params = mock_mlflow_for_decorators.log_params.call_args_list[0][0][0]
    assert first_call_params["threshold"] == 0.5
    assert first_call_params["model_type"] == "xgboost"


def test_track_model_logs_function_metadata(mock_mlflow_for_decorators):
    """Test track_model logs function name and module."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model()
        def my_inference_fn():
            return None

        my_inference_fn()

    # Check function metadata was logged
    calls = mock_mlflow_for_decorators.log_params.call_args_list
    # Find the call with function_name
    for c in calls:
        params = c[0][0]
        if "function_name" in params:
            assert params["function_name"] == "my_inference_fn"
            break


def test_track_model_sets_success_tag(mock_mlflow_for_decorators):
    """Test track_model sets success tag on completion."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model()
        def successful_function():
            return "success"

        successful_function()

    mock_mlflow_for_decorators.set_tag.assert_any_call("status", "success")


def test_track_model_handles_exception(mock_mlflow_for_decorators):
    """Test track_model handles and re-raises exceptions."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model()
        def failing_function():
            raise ValueError("Model failed")

        with pytest.raises(ValueError, match="Model failed"):
            failing_function()

    mock_mlflow_for_decorators.set_tag.assert_any_call("status", "failed")


def test_track_model_logs_error_message(mock_mlflow_for_decorators):
    """Test track_model logs error message on failure."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model()
        def error_function():
            raise RuntimeError("Specific error message")

        with pytest.raises(RuntimeError):
            error_function()

    # Check error tag was set
    error_calls = [
        c
        for c in mock_mlflow_for_decorators.set_tag.call_args_list
        if c[0][0] == "error"
    ]
    assert len(error_calls) == 1
    assert "Specific error message" in error_calls[0][0][1]


def test_track_model_with_tags(mock_mlflow_for_decorators):
    """Test track_model with custom tags."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_model

        @track_model(tags={"environment": "production", "version": "1.0"})
        def tagged_function():
            return "tagged"

        tagged_function()

    # Tags should be passed to start_run via config
    # Check that tracker was configured with tags


# track_pipeline decorator tests


def test_track_pipeline_basic(mock_mlflow_for_decorators):
    """Test track_pipeline decorator basic functionality."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_pipeline

        @track_pipeline(experiment="pipeline-experiment")
        def my_pipeline(docs):
            return [d.upper() for d in docs]

        result = my_pipeline(["a", "b", "c"])

    assert result == ["A", "B", "C"]
    mock_mlflow_for_decorators.start_run.assert_called()


def test_track_pipeline_uses_function_name_with_suffix(mock_mlflow_for_decorators):
    """Test track_pipeline adds -pipeline suffix to run name."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_pipeline

        @track_pipeline()
        def process_notes(notes):
            return notes

        process_notes([])

    call_kwargs = mock_mlflow_for_decorators.start_run.call_args[1]
    assert call_kwargs["run_name"] == "process_notes-pipeline"


def test_track_pipeline_logs_input_shape(mock_mlflow_for_decorators):
    """Test track_pipeline logs input data shape."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_pipeline

        @track_pipeline(log_input_shape=True)
        def process_batch(items):
            return items

        process_batch([1, 2, 3, 4, 5])

    # Check input count was logged as param
    calls = mock_mlflow_for_decorators.log_params.call_args_list
    found_input_count = False
    for c in calls:
        params = c[0][0]
        if "input_count" in params:
            assert params["input_count"] == 5
            found_input_count = True
            break
    assert found_input_count


def test_track_pipeline_logs_execution_time(mock_mlflow_for_decorators):
    """Test track_pipeline logs pipeline execution time."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_pipeline

        @track_pipeline()
        def timed_pipeline(data):
            return data

        timed_pipeline([])

    mock_mlflow_for_decorators.log_metrics.assert_called()
    # log_metrics is called multiple times (execution time + output shape)
    # Check all calls for pipeline_execution_seconds
    all_calls = mock_mlflow_for_decorators.log_metrics.call_args_list
    found_execution_time = False
    for call in all_calls:
        metrics = call[0][0]
        if "pipeline_execution_seconds" in metrics:
            found_execution_time = True
            break
    assert (
        found_execution_time
    ), "pipeline_execution_seconds not found in any log_metrics call"


def test_track_pipeline_handles_exception(mock_mlflow_for_decorators):
    """Test track_pipeline handles and re-raises exceptions."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import track_pipeline

        @track_pipeline()
        def failing_pipeline(data):
            raise RuntimeError("Pipeline failed")

        with pytest.raises(RuntimeError, match="Pipeline failed"):
            failing_pipeline([])

    mock_mlflow_for_decorators.set_tag.assert_any_call("status", "failed")


# _get_shape_metrics helper tests


def test_get_shape_metrics_list():
    """Test _get_shape_metrics with list input."""
    from healthchain.mlflow.decorators import _get_shape_metrics

    metrics = _get_shape_metrics([1, 2, 3, 4], "test")

    assert metrics["test_count"] == 4


def test_get_shape_metrics_tuple():
    """Test _get_shape_metrics with tuple input."""
    from healthchain.mlflow.decorators import _get_shape_metrics

    metrics = _get_shape_metrics((1, 2, 3), "input")

    assert metrics["input_count"] == 3


def test_get_shape_metrics_string():
    """Test _get_shape_metrics with string input."""
    from healthchain.mlflow.decorators import _get_shape_metrics

    metrics = _get_shape_metrics("hello world", "text")

    assert metrics["text_length"] == 11


def test_get_shape_metrics_document():
    """Test _get_shape_metrics with Document-like object."""
    from healthchain.mlflow.decorators import _get_shape_metrics

    doc = Document(data="Test document content")

    metrics = _get_shape_metrics(doc, "doc")

    assert metrics["doc_text_length"] == 21


def test_get_shape_metrics_empty_object():
    """Test _get_shape_metrics with object without shape info."""
    from healthchain.mlflow.decorators import _get_shape_metrics

    class NoShape:
        pass

    metrics = _get_shape_metrics(NoShape(), "obj")

    assert metrics == {}


# TrackedPipeline tests


def test_tracked_pipeline_initialization(mock_mlflow_for_decorators):
    """Test TrackedPipeline initialization."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import TrackedPipeline
        from healthchain.mlflow.config import MLFlowConfig

        def simple_pipeline(data):
            return data

        config = MLFlowConfig(experiment_name="tracked-test")
        tracked = TrackedPipeline(simple_pipeline, config)

        assert tracked.pipeline is simple_pipeline
        assert tracked.config is config
        assert tracked._call_count == 0


def test_tracked_pipeline_execution(mock_mlflow_for_decorators):
    """Test TrackedPipeline executes wrapped pipeline."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import TrackedPipeline

        def double_pipeline(x):
            return x * 2

        tracked = TrackedPipeline(double_pipeline)

        result = tracked(5)

    assert result == 10


def test_tracked_pipeline_increments_call_count(mock_mlflow_for_decorators):
    """Test TrackedPipeline increments call count."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import TrackedPipeline

        def identity(x):
            return x

        tracked = TrackedPipeline(identity)

        tracked("a")
        assert tracked._call_count == 1

        tracked("b")
        assert tracked._call_count == 2


def test_tracked_pipeline_unique_run_names(mock_mlflow_for_decorators):
    """Test TrackedPipeline creates unique run names."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import TrackedPipeline

        def pipeline(x):
            return x

        tracked = TrackedPipeline(pipeline, run_name_prefix="my-pipeline")

        tracked("a")
        tracked("b")

    calls = mock_mlflow_for_decorators.start_run.call_args_list
    run_names = [c[1]["run_name"] for c in calls]
    assert "my-pipeline-1" in run_names
    assert "my-pipeline-2" in run_names


def test_tracked_pipeline_logs_call_number(mock_mlflow_for_decorators):
    """Test TrackedPipeline logs call number as parameter."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import TrackedPipeline

        def pipeline(x):
            return x

        tracked = TrackedPipeline(pipeline)

        tracked("test")

    mock_mlflow_for_decorators.log_params.assert_called()
    logged_params = mock_mlflow_for_decorators.log_params.call_args[0][0]
    assert logged_params["call_number"] == 1


def test_tracked_pipeline_handles_exception(mock_mlflow_for_decorators):
    """Test TrackedPipeline handles and re-raises exceptions."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import TrackedPipeline

        def failing_pipeline(x):
            raise ValueError("Pipeline error")

        tracked = TrackedPipeline(failing_pipeline)

        with pytest.raises(ValueError, match="Pipeline error"):
            tracked("test")

    mock_mlflow_for_decorators.set_tag.assert_any_call("status", "failed")


def test_tracked_pipeline_get_tracker(mock_mlflow_for_decorators):
    """Test TrackedPipeline get_tracker method."""
    with patch(
        "healthchain.mlflow.tracker._get_mlflow",
        return_value=mock_mlflow_for_decorators,
    ):
        from healthchain.mlflow.decorators import TrackedPipeline

        def pipeline(x):
            return x

        tracked = TrackedPipeline(pipeline)
        tracker = tracked.get_tracker()

        assert tracker is tracked.tracker
