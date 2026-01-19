"""Configuration models for MLFlow integration."""

import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class MLFlowConfig(BaseModel):
    """Configuration for MLFlow experiment tracking.

    This Pydantic model defines the configuration options for connecting to
    and using MLFlow for experiment tracking in HealthChain pipelines.

    Attributes:
        tracking_uri: URI for the MLFlow tracking server. Can be a local path
            (e.g., "mlruns" or "./experiments") or a remote server URL
            (e.g., "http://localhost:5000").
        experiment_name: Name of the MLFlow experiment. If the experiment
            doesn't exist, it will be created.
        artifact_location: Optional custom location for storing artifacts.
            If not specified, uses the default location for the tracking URI.
        tags: Default tags to apply to all runs created with this config.
        log_system_metrics: Whether to log system metrics (CPU, memory, etc.)
            during runs. Requires psutil to be installed.
        log_models: Whether to automatically log models during runs.
        registry_uri: Optional separate URI for the model registry.
            If not specified, uses the tracking_uri.

    Example:
        >>> config = MLFlowConfig(
        ...     tracking_uri="mlruns",
        ...     experiment_name="sepsis-prediction",
        ...     tags={"team": "ml-research", "project": "clinical-ai"}
        ... )
        >>> tracker = MLFlowTracker(config)
    """

    tracking_uri: str = Field(
        default="mlruns",
        description="URI for the MLFlow tracking server (local path or remote URL)",
    )
    experiment_name: str = Field(
        default="healthchain-default",
        description="Name of the MLFlow experiment",
    )
    artifact_location: Optional[str] = Field(
        default=None,
        description="Custom location for storing artifacts",
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Default tags to apply to all runs",
    )
    log_system_metrics: bool = Field(
        default=False,
        description="Whether to log system metrics during runs",
    )
    log_models: bool = Field(
        default=True,
        description="Whether to automatically log models",
    )
    registry_uri: Optional[str] = Field(
        default=None,
        description="Optional separate URI for the model registry",
    )

    @model_validator(mode="after")
    def _validate_config(self) -> "MLFlowConfig":
        """Validate configuration after all fields are set."""
        if not self.tracking_uri:
            raise ValueError("tracking_uri cannot be empty")
        if not self.experiment_name:
            raise ValueError("experiment_name cannot be empty")
        return self

    def to_mlflow_kwargs(self) -> Dict[str, Any]:
        """Convert config to kwargs for MLFlow client initialization.

        Returns:
            Dictionary of keyword arguments for mlflow.set_tracking_uri
            and mlflow.set_experiment.
        """
        kwargs = {
            "tracking_uri": self.tracking_uri,
            "experiment_name": self.experiment_name,
        }
        if self.artifact_location:
            kwargs["artifact_location"] = self.artifact_location
        if self.registry_uri:
            kwargs["registry_uri"] = self.registry_uri
        return kwargs

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
        extra = "forbid"
