"""MLflow integration for HealthChain experiment tracking.

This module provides healthcare-specific context and FHIR Provenance generation
for MLflow experiment tracking. It is designed to work with MLflow directly
rather than wrapping it.

Installation:
    pip install healthchain[mlflow]

Example:
    >>> import mlflow
    >>> from healthchain.mlflow import HealthcareRunContext, log_healthcare_context
    >>>
    >>> context = HealthcareRunContext(
    ...     model_id="sepsis-predictor",
    ...     version="1.0.0",
    ...     purpose="Early sepsis detection",
    ... )
    >>>
    >>> mlflow.set_experiment("clinical-nlp")
    >>> with mlflow.start_run(run_name="evaluation-v1"):
    ...     log_healthcare_context(context)
    ...     # Your training/evaluation code here
    ...     mlflow.log_metrics({"accuracy": 0.92})
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Track whether mlflow is available
_MLFLOW_AVAILABLE = False

try:
    import mlflow as _mlflow

    _MLFLOW_AVAILABLE = True
except ImportError:
    _mlflow = None
    logger.debug("MLflow not installed. Install with: pip install healthchain[mlflow]")


def is_mlflow_available() -> bool:
    """Check if MLflow is installed and available.

    Returns:
        True if MLflow is available, False otherwise
    """
    return _MLFLOW_AVAILABLE


# Always import context classes (they don't require mlflow)
from healthchain.mlflow.context import HealthcareRunContext, PatientContext  # noqa: E402


def log_healthcare_context(
    context: HealthcareRunContext,
    log_provenance: bool = True,
) -> Dict[str, Any]:
    """Log healthcare context to the active MLflow run.

    This function logs healthcare-specific metadata to MLflow, including
    model information, patient cohort context, and optionally a FHIR
    Provenance resource for audit trails.

    If context.tracking_uri is set (populated automatically by
    HealthcareRunContext.from_app_config()), the MLflow tracking URI is
    configured before logging.

    Args:
        context: HealthcareRunContext with healthcare metadata
        log_provenance: Whether to log FHIR Provenance as an artifact.
            Defaults to True.

    Returns:
        Dictionary of logged parameters for reference

    Raises:
        ImportError: If MLflow is not installed
        RuntimeError: If no MLflow run is active

    Example:
        >>> import mlflow
        >>> from healthchain.config.appconfig import AppConfig
        >>> from healthchain.mlflow import HealthcareRunContext, log_healthcare_context
        >>>
        >>> config = AppConfig.load()
        >>> context = HealthcareRunContext.from_app_config(
        ...     config,
        ...     model_id="clinical-ner",
        ...     purpose="Entity extraction from clinical notes",
        ... )
        >>>
        >>> with mlflow.start_run():
        ...     log_healthcare_context(context)
    """
    if not _MLFLOW_AVAILABLE:
        raise ImportError(
            "MLflow is not installed. Install with: pip install healthchain[mlflow]"
        )

    if context.tracking_uri is not None:
        _mlflow.set_tracking_uri(context.tracking_uri)

    # Check for active run
    if _mlflow.active_run() is None:
        raise RuntimeError(
            "No active MLflow run. Call mlflow.start_run() first or use as context manager."
        )

    # Build parameters to log
    params = {
        "healthcare.model_id": context.model_id,
        "healthcare.model_version": context.version,
    }

    if context.organization:
        params["healthcare.organization"] = context.organization

    if context.purpose:
        params["healthcare.purpose"] = context.purpose

    if context.patient_context:
        params["healthcare.patient_cohort"] = context.patient_context.cohort
        if context.patient_context.age_range:
            params["healthcare.patient_age_range"] = context.patient_context.age_range
        if context.patient_context.sample_size:
            params["healthcare.patient_sample_size"] = (
                context.patient_context.sample_size
            )

    if context.data_sources:
        params["healthcare.data_sources"] = ", ".join(context.data_sources)

    if context.regulatory_tags:
        params["healthcare.regulatory_tags"] = ", ".join(context.regulatory_tags)

    # Log parameters
    _mlflow.log_params(params)

    # Set healthcare-specific tags
    _mlflow.set_tag("healthchain.model_id", context.model_id)
    _mlflow.set_tag("healthchain.version", context.version)

    # Log custom metadata as tags (avoids MLflow param value length limits)
    for key, value in context.custom_metadata.items():
        _mlflow.set_tag(f"healthcare.custom.{key}", str(value))

    # Log FHIR Provenance as artifact if requested
    if log_provenance:
        provenance = context.to_fhir_provenance()
        if provenance:
            _mlflow.log_dict(
                provenance.model_dump(exclude_none=True),
                "fhir_provenance.json",
            )
            _mlflow.set_tag("healthchain.has_provenance", "true")
            logger.info("Logged FHIR Provenance for healthcare audit trail")

    return params


__all__ = [
    "HealthcareRunContext",
    "PatientContext",
    "log_healthcare_context",
    "is_mlflow_available",
]
