"""Core MLFlow experiment tracking operations."""

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional

from healthchain.mlflow.config import MLFlowConfig

if TYPE_CHECKING:
    from healthchain.mlflow.context import HealthcareRunContext

logger = logging.getLogger(__name__)

# Lazy import for optional dependency
_mlflow = None


def _get_mlflow():
    """Lazily import mlflow to handle optional dependency."""
    global _mlflow
    if _mlflow is None:
        try:
            import mlflow

            _mlflow = mlflow
        except ImportError:
            raise ImportError(
                "MLFlow is not installed. Install it with: pip install healthchain[mlflow]"
            )
    return _mlflow


class MLFlowTracker:
    """Core MLFlow experiment tracking operations.

    The MLFlowTracker provides a simplified interface for MLFlow experiment
    tracking, designed for healthcare AI workflows. It handles experiment
    setup, run management, and logging of parameters, metrics, and artifacts.

    Features:
        - Automatic experiment creation and run management
        - Context manager support for run lifecycle
        - Healthcare-specific metadata logging
        - Integration with FHIR Provenance for audit trails

    Attributes:
        config: MLFlowConfig instance with tracking settings
        _active_run: Reference to the currently active MLFlow run
        _experiment_id: ID of the current experiment

    Example:
        >>> config = MLFlowConfig(
        ...     tracking_uri="mlruns",
        ...     experiment_name="sepsis-prediction"
        ... )
        >>> tracker = MLFlowTracker(config)
        >>> with tracker.start_run(run_name="v1.2.0"):
        ...     tracker.log_params({"model_type": "xgboost", "threshold": 0.5})
        ...     predictions = model.predict(X)
        ...     tracker.log_metrics({"accuracy": 0.92, "auc": 0.87})
    """

    def __init__(self, config: MLFlowConfig) -> None:
        """Initialize the MLFlowTracker.

        Args:
            config: MLFlowConfig instance with tracking settings
        """
        self.config = config
        self._active_run: Optional[Any] = None
        self._experiment_id: Optional[str] = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure MLFlow is configured and ready for tracking."""
        if self._initialized:
            return

        mlflow = _get_mlflow()

        # Set tracking URI
        mlflow.set_tracking_uri(self.config.tracking_uri)
        logger.debug(f"MLFlow tracking URI set to: {self.config.tracking_uri}")

        # Set registry URI if specified
        if self.config.registry_uri:
            mlflow.set_registry_uri(self.config.registry_uri)
            logger.debug(f"MLFlow registry URI set to: {self.config.registry_uri}")

        # Get or create experiment
        experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
        if experiment is None:
            self._experiment_id = mlflow.create_experiment(
                self.config.experiment_name,
                artifact_location=self.config.artifact_location,
            )
            logger.info(
                f"Created MLFlow experiment: {self.config.experiment_name} "
                f"(ID: {self._experiment_id})"
            )
        else:
            self._experiment_id = experiment.experiment_id
            logger.debug(
                f"Using existing MLFlow experiment: {self.config.experiment_name} "
                f"(ID: {self._experiment_id})"
            )

        mlflow.set_experiment(self.config.experiment_name)
        self._initialized = True

    @classmethod
    def from_config(cls, config: MLFlowConfig) -> "MLFlowTracker":
        """Create an MLFlowTracker from a configuration object.

        Args:
            config: MLFlowConfig instance

        Returns:
            Configured MLFlowTracker instance
        """
        return cls(config)

    @contextmanager
    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        nested: bool = False,
        description: Optional[str] = None,
    ) -> Generator["MLFlowTracker", None, None]:
        """Start an MLFlow run as a context manager.

        Args:
            run_name: Optional name for the run
            tags: Optional additional tags for this run (merged with config tags)
            nested: Whether this is a nested run within an existing run
            description: Optional description for the run

        Yields:
            Self for method chaining within the context

        Example:
            >>> with tracker.start_run(run_name="experiment-v1") as run:
            ...     run.log_params({"learning_rate": 0.01})
            ...     run.log_metrics({"accuracy": 0.95})
        """
        self._ensure_initialized()
        mlflow = _get_mlflow()

        # Merge config tags with run-specific tags
        all_tags = {**self.config.tags, **(tags or {})}
        if description:
            all_tags["mlflow.note.content"] = description

        try:
            self._active_run = mlflow.start_run(
                experiment_id=self._experiment_id,
                run_name=run_name,
                tags=all_tags if all_tags else None,
                nested=nested,
            )
            logger.info(
                f"Started MLFlow run: {run_name or self._active_run.info.run_id}"
            )
            yield self
        finally:
            if self._active_run:
                mlflow.end_run()
                logger.debug(f"Ended MLFlow run: {self._active_run.info.run_id}")
                self._active_run = None

    def log_params(self, params: Dict[str, Any]) -> None:
        """Log parameters to the active run.

        Parameters are key-value pairs that describe the configuration
        of an experiment, such as hyperparameters or model settings.

        Args:
            params: Dictionary of parameter names and values

        Raises:
            RuntimeError: If no run is currently active
        """
        if self._active_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        mlflow = _get_mlflow()

        # Convert non-string values to strings for MLFlow compatibility
        sanitized_params = {}
        for key, value in params.items():
            if value is None:
                sanitized_params[key] = "None"
            elif isinstance(value, (list, dict)):
                import json

                sanitized_params[key] = json.dumps(value)
            else:
                sanitized_params[key] = value

        mlflow.log_params(sanitized_params)
        logger.debug(f"Logged {len(params)} parameters")

    def log_metrics(
        self,
        metrics: Dict[str, float],
        step: Optional[int] = None,
    ) -> None:
        """Log metrics to the active run.

        Metrics are numerical values that measure the performance of a model,
        such as accuracy, loss, or AUC.

        Args:
            metrics: Dictionary of metric names and values
            step: Optional step number for time-series metrics

        Raises:
            RuntimeError: If no run is currently active
        """
        if self._active_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        mlflow = _get_mlflow()
        mlflow.log_metrics(metrics, step=step)
        logger.debug(f"Logged {len(metrics)} metrics at step {step}")

    def log_metric(
        self,
        key: str,
        value: float,
        step: Optional[int] = None,
    ) -> None:
        """Log a single metric to the active run.

        Args:
            key: Metric name
            value: Metric value
            step: Optional step number for time-series metrics

        Raises:
            RuntimeError: If no run is currently active
        """
        self.log_metrics({key: value}, step=step)

    def log_artifact(
        self,
        local_path: str,
        artifact_path: Optional[str] = None,
    ) -> None:
        """Log a local file or directory as an artifact.

        Artifacts are files associated with a run, such as model files,
        plots, or data files.

        Args:
            local_path: Path to the local file or directory to log
            artifact_path: Optional path within the artifact store

        Raises:
            RuntimeError: If no run is currently active
        """
        if self._active_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        mlflow = _get_mlflow()
        mlflow.log_artifact(local_path, artifact_path)
        logger.debug(f"Logged artifact: {local_path}")

    def log_artifacts(
        self,
        local_dir: str,
        artifact_path: Optional[str] = None,
    ) -> None:
        """Log all files in a directory as artifacts.

        Args:
            local_dir: Path to the local directory to log
            artifact_path: Optional path within the artifact store

        Raises:
            RuntimeError: If no run is currently active
        """
        if self._active_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        mlflow = _get_mlflow()
        mlflow.log_artifacts(local_dir, artifact_path)
        logger.debug(f"Logged artifacts from: {local_dir}")

    def log_dict(
        self,
        dictionary: Dict[str, Any],
        artifact_file: str,
    ) -> None:
        """Log a dictionary as a JSON artifact.

        Args:
            dictionary: Dictionary to log
            artifact_file: Name of the artifact file (e.g., "config.json")

        Raises:
            RuntimeError: If no run is currently active
        """
        if self._active_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        mlflow = _get_mlflow()
        mlflow.log_dict(dictionary, artifact_file)
        logger.debug(f"Logged dictionary to: {artifact_file}")

    def log_text(
        self,
        text: str,
        artifact_file: str,
    ) -> None:
        """Log text content as an artifact.

        Args:
            text: Text content to log
            artifact_file: Name of the artifact file (e.g., "notes.txt")

        Raises:
            RuntimeError: If no run is currently active
        """
        if self._active_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        mlflow = _get_mlflow()
        mlflow.log_text(text, artifact_file)
        logger.debug(f"Logged text to: {artifact_file}")

    def set_tags(self, tags: Dict[str, str]) -> None:
        """Set tags on the active run.

        Tags are key-value pairs that provide additional metadata
        about a run, useful for filtering and organizing runs.

        Args:
            tags: Dictionary of tag names and values

        Raises:
            RuntimeError: If no run is currently active
        """
        if self._active_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        mlflow = _get_mlflow()
        for key, value in tags.items():
            mlflow.set_tag(key, value)
        logger.debug(f"Set {len(tags)} tags")

    def set_tag(self, key: str, value: str) -> None:
        """Set a single tag on the active run.

        Args:
            key: Tag name
            value: Tag value

        Raises:
            RuntimeError: If no run is currently active
        """
        self.set_tags({key: value})

    def log_healthcare_context(self, context: "HealthcareRunContext") -> None:
        """Log healthcare-specific context to the active run.

        This method logs healthcare metadata including model information,
        patient context (anonymized), and FHIR Provenance data for audit trails.

        Args:
            context: HealthcareRunContext instance with healthcare metadata

        Raises:
            RuntimeError: If no run is currently active
        """
        if self._active_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        # Log context as parameters
        context_params = {
            "healthcare.model_id": context.model_id,
            "healthcare.model_version": context.version,
        }

        if context.patient_context:
            context_params["healthcare.patient_cohort"] = context.patient_context.cohort
            if context.patient_context.age_range:
                context_params["healthcare.patient_age_range"] = (
                    context.patient_context.age_range
                )

        self.log_params(context_params)

        # Set healthcare-specific tags
        self.set_tags(
            {
                "healthchain.model_id": context.model_id,
                "healthchain.version": context.version,
                "healthchain.has_provenance": "true",
            }
        )

        # Log FHIR Provenance as artifact if available
        provenance = context.to_fhir_provenance()
        if provenance:
            self.log_dict(
                provenance.model_dump(exclude_none=True),
                "fhir_provenance.json",
            )
            logger.info("Logged FHIR Provenance for healthcare audit trail")

    def get_run_id(self) -> Optional[str]:
        """Get the ID of the currently active run.

        Returns:
            Run ID string if a run is active, None otherwise
        """
        if self._active_run is None:
            return None
        return self._active_run.info.run_id

    def get_artifact_uri(self) -> Optional[str]:
        """Get the artifact URI for the currently active run.

        Returns:
            Artifact URI string if a run is active, None otherwise
        """
        if self._active_run is None:
            return None
        return self._active_run.info.artifact_uri

    def get_experiment_id(self) -> Optional[str]:
        """Get the ID of the current experiment.

        Returns:
            Experiment ID string if initialized, None otherwise
        """
        return self._experiment_id

    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments in the tracking server.

        Returns:
            List of experiment dictionaries with id, name, and artifact_location
        """
        self._ensure_initialized()
        mlflow = _get_mlflow()

        experiments = mlflow.search_experiments()
        return [
            {
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "artifact_location": exp.artifact_location,
                "lifecycle_stage": exp.lifecycle_stage,
            }
            for exp in experiments
        ]

    def list_runs(
        self,
        experiment_name: Optional[str] = None,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """List runs for an experiment.

        Args:
            experiment_name: Name of the experiment (uses current if not specified)
            max_results: Maximum number of runs to return

        Returns:
            List of run dictionaries with run_id, status, and metrics
        """
        self._ensure_initialized()
        mlflow = _get_mlflow()

        exp_name = experiment_name or self.config.experiment_name
        experiment = mlflow.get_experiment_by_name(exp_name)
        if experiment is None:
            logger.warning(f"Experiment not found: {exp_name}")
            return []

        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=max_results,
        )

        return runs.to_dict(orient="records") if len(runs) > 0 else []
