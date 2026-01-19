"""Tests for MLFlowConfig."""

import pytest
from pydantic import ValidationError

from healthchain.mlflow.config import MLFlowConfig


def test_mlflow_config_default_values():
    """Test MLFlowConfig with default values."""
    config = MLFlowConfig()

    assert config.tracking_uri == "mlruns"
    assert config.experiment_name == "healthchain-default"
    assert config.artifact_location is None
    assert config.tags == {}
    assert config.log_system_metrics is False
    assert config.log_models is True
    assert config.registry_uri is None


def test_mlflow_config_custom_values():
    """Test MLFlowConfig with custom values."""
    config = MLFlowConfig(
        tracking_uri="http://localhost:5000",
        experiment_name="my-experiment",
        artifact_location="/custom/path",
        tags={"team": "ml-team", "version": "1.0"},
        log_system_metrics=True,
        log_models=False,
        registry_uri="http://registry:5001",
    )

    assert config.tracking_uri == "http://localhost:5000"
    assert config.experiment_name == "my-experiment"
    assert config.artifact_location == "/custom/path"
    assert config.tags == {"team": "ml-team", "version": "1.0"}
    assert config.log_system_metrics is True
    assert config.log_models is False
    assert config.registry_uri == "http://registry:5001"


def test_mlflow_config_empty_tracking_uri_raises_error():
    """Test that empty tracking_uri raises validation error."""
    with pytest.raises(ValidationError):
        MLFlowConfig(tracking_uri="")


def test_mlflow_config_empty_experiment_name_raises_error():
    """Test that empty experiment_name raises validation error."""
    with pytest.raises(ValidationError):
        MLFlowConfig(experiment_name="")


def test_mlflow_config_extra_fields_forbidden():
    """Test that extra fields are not allowed."""
    with pytest.raises(ValidationError):
        MLFlowConfig(tracking_uri="mlruns", unknown_field="value")


def test_mlflow_config_to_mlflow_kwargs_basic():
    """Test to_mlflow_kwargs with basic config."""
    config = MLFlowConfig(
        tracking_uri="mlruns",
        experiment_name="test-experiment",
    )

    kwargs = config.to_mlflow_kwargs()

    assert kwargs == {
        "tracking_uri": "mlruns",
        "experiment_name": "test-experiment",
    }


def test_mlflow_config_to_mlflow_kwargs_with_optional_fields():
    """Test to_mlflow_kwargs with all optional fields."""
    config = MLFlowConfig(
        tracking_uri="http://localhost:5000",
        experiment_name="test-experiment",
        artifact_location="/artifacts",
        registry_uri="http://registry:5001",
    )

    kwargs = config.to_mlflow_kwargs()

    assert kwargs == {
        "tracking_uri": "http://localhost:5000",
        "experiment_name": "test-experiment",
        "artifact_location": "/artifacts",
        "registry_uri": "http://registry:5001",
    }


def test_mlflow_config_tags_not_included_in_kwargs():
    """Test that tags are not included in to_mlflow_kwargs output."""
    config = MLFlowConfig(
        tracking_uri="mlruns",
        experiment_name="test",
        tags={"key": "value"},
    )

    kwargs = config.to_mlflow_kwargs()

    assert "tags" not in kwargs


def test_mlflow_config_validate_assignment():
    """Test that assignment validation works."""
    config = MLFlowConfig()

    # Valid assignment
    config.tracking_uri = "new-uri"
    assert config.tracking_uri == "new-uri"

    # Invalid assignment should raise
    with pytest.raises(ValidationError):
        config.tracking_uri = ""


def test_mlflow_config_immutable_tags():
    """Test that tags can be modified after creation."""
    config = MLFlowConfig(tags={"initial": "value"})

    config.tags["new_key"] = "new_value"

    assert config.tags == {"initial": "value", "new_key": "new_value"}
