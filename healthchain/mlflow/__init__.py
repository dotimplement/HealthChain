"""MLFlow integration for HealthChain experiment tracking.

This module provides experiment tracking capabilities for healthcare AI
applications using MLFlow. It includes:

- MLFlowConfig: Configuration for MLFlow tracking
- MLFlowTracker: Core tracking operations
- HealthcareRunContext: Healthcare-specific metadata with FHIR Provenance
- MLFlowComponent: Pipeline component for automatic tracking
- Decorators: @track_model, @track_pipeline for easy integration

Installation:
    pip install healthchain[mlflow]

Example:
    >>> from healthchain.mlflow import MLFlowTracker, MLFlowConfig
    >>>
    >>> config = MLFlowConfig(
    ...     tracking_uri="mlruns",
    ...     experiment_name="sepsis-prediction"
    ... )
    >>> tracker = MLFlowTracker(config)
    >>>
    >>> with tracker.start_run(run_name="v1.2.0"):
    ...     tracker.log_params({"model_type": "xgboost"})
    ...     tracker.log_metrics({"accuracy": 0.92})
"""

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Track whether mlflow is available
_MLFLOW_AVAILABLE = False

try:
    import mlflow as _mlflow

    _MLFLOW_AVAILABLE = True
except ImportError:
    _mlflow = None
    logger.debug("MLFlow not installed. Install with: pip install healthchain[mlflow]")


def is_mlflow_available() -> bool:
    """Check if MLFlow is installed and available.

    Returns:
        True if MLFlow is available, False otherwise
    """
    return _MLFLOW_AVAILABLE


# Always import config and context (they don't require mlflow)
from healthchain.mlflow.config import MLFlowConfig  # noqa: E402
from healthchain.mlflow.context import HealthcareRunContext, PatientContext  # noqa: E402

# Conditionally import components that require mlflow
if _MLFLOW_AVAILABLE or TYPE_CHECKING:
    from healthchain.mlflow.tracker import MLFlowTracker
    from healthchain.mlflow.components import MLFlowComponent
    from healthchain.mlflow.decorators import track_model, track_pipeline

    __all__ = [
        # Core
        "MLFlowConfig",
        "MLFlowTracker",
        # Healthcare context
        "HealthcareRunContext",
        "PatientContext",
        # Pipeline integration
        "MLFlowComponent",
        # Decorators
        "track_model",
        "track_pipeline",
        # Utilities
        "is_mlflow_available",
    ]
else:
    # Provide helpful error messages when mlflow is not installed
    def _mlflow_not_installed(*args, **kwargs):
        raise ImportError(
            "MLFlow is not installed. Install it with: pip install healthchain[mlflow]"
        )

    class MLFlowTracker:
        """MLFlow is not installed. Install with: pip install healthchain[mlflow]"""

        def __init__(self, *args, **kwargs):
            _mlflow_not_installed()

    class MLFlowComponent:
        """MLFlow is not installed. Install with: pip install healthchain[mlflow]"""

        def __init__(self, *args, **kwargs):
            _mlflow_not_installed()

    def track_model(*args, **kwargs):
        """MLFlow is not installed. Install with: pip install healthchain[mlflow]"""
        _mlflow_not_installed()

    def track_pipeline(*args, **kwargs):
        """MLFlow is not installed. Install with: pip install healthchain[mlflow]"""
        _mlflow_not_installed()

    __all__ = [
        # Core
        "MLFlowConfig",
        "MLFlowTracker",
        # Healthcare context
        "HealthcareRunContext",
        "PatientContext",
        # Pipeline integration
        "MLFlowComponent",
        # Decorators
        "track_model",
        "track_pipeline",
        # Utilities
        "is_mlflow_available",
    ]
