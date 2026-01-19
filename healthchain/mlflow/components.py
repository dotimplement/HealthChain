"""Pipeline component for MLFlow tracking integration."""

import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, Optional, TypeVar

from healthchain.io.containers import DataContainer
from healthchain.pipeline.components.base import BaseComponent

if TYPE_CHECKING:
    from healthchain.mlflow.tracker import MLFlowTracker

logger = logging.getLogger(__name__)

T = TypeVar("T")


class MLFlowComponent(BaseComponent[T], Generic[T]):
    """Pipeline component for automatic MLFlow tracking.

    This component integrates with HealthChain pipelines to automatically
    track metrics, parameters, and artifacts during pipeline execution.
    It can be added to any pipeline stage to capture execution data.

    Features:
        - Automatic execution time tracking
        - Input/output shape logging (when available)
        - Custom metric extraction via callbacks
        - Healthcare context logging with FHIR Provenance

    Attributes:
        tracker: MLFlowTracker instance for logging
        track_predictions: Whether to log prediction counts
        track_timing: Whether to log execution time
        metric_extractors: Optional callbacks to extract custom metrics
        prefix: Prefix for metric/parameter names

    Example:
        >>> from healthchain.pipeline import Pipeline
        >>> from healthchain.mlflow import MLFlowComponent, MLFlowTracker
        >>>
        >>> tracker = MLFlowTracker(config)
        >>> pipeline = Pipeline[Document]()
        >>> pipeline.add_node(SpacyNLP.from_model_id("en_core_web_sm"))
        >>> pipeline.add_node(
        ...     MLFlowComponent(tracker, track_predictions=True),
        ...     stage="tracking"
        ... )
        >>>
        >>> with tracker.start_run():
        ...     result = pipeline(doc)  # Automatically logged
    """

    def __init__(
        self,
        tracker: "MLFlowTracker",
        track_predictions: bool = True,
        track_timing: bool = True,
        metric_extractors: Optional[
            Dict[str, Callable[[DataContainer[T]], float]]
        ] = None,
        prefix: str = "pipeline",
    ) -> None:
        """Initialize the MLFlowComponent.

        Args:
            tracker: MLFlowTracker instance for logging
            track_predictions: Whether to log prediction/output counts
            track_timing: Whether to log execution time
            metric_extractors: Optional dict of metric names to extraction functions.
                Each function receives the DataContainer and returns a float value.
            prefix: Prefix for metric/parameter names (default: "pipeline")
        """
        self.tracker = tracker
        self.track_predictions = track_predictions
        self.track_timing = track_timing
        self.metric_extractors = metric_extractors or {}
        self.prefix = prefix
        self._start_time: Optional[float] = None
        self._call_count: int = 0

    def __call__(self, data: DataContainer[T]) -> DataContainer[T]:
        """Process data and log tracking information.

        This method logs execution metrics to MLFlow if a run is active.
        If no run is active, it logs a debug message and passes data through.

        Args:
            data: Input data container

        Returns:
            The same data container (this component is pass-through)
        """
        # Check if tracker has an active run
        run_id = self.tracker.get_run_id()
        if run_id is None:
            logger.debug("MLFlowComponent: No active run, skipping tracking")
            return data

        self._call_count += 1
        metrics: Dict[str, float] = {}

        # Track timing
        if self.track_timing:
            if self._start_time is None:
                self._start_time = time.time()
            elapsed = time.time() - self._start_time
            metrics[f"{self.prefix}.elapsed_seconds"] = elapsed

        # Track call count
        metrics[f"{self.prefix}.call_count"] = float(self._call_count)

        # Track predictions/outputs if available
        if self.track_predictions:
            metrics.update(self._extract_output_metrics(data))

        # Run custom metric extractors
        for metric_name, extractor in self.metric_extractors.items():
            try:
                value = extractor(data)
                metrics[f"{self.prefix}.{metric_name}"] = value
            except Exception as e:
                logger.warning(f"Failed to extract metric '{metric_name}': {e}")

        # Log metrics
        if metrics:
            try:
                self.tracker.log_metrics(metrics, step=self._call_count)
            except Exception as e:
                logger.warning(f"Failed to log metrics: {e}")

        return data

    def _extract_output_metrics(self, data: DataContainer[T]) -> Dict[str, float]:
        """Extract output-related metrics from the data container.

        Args:
            data: Data container to extract metrics from

        Returns:
            Dictionary of metric names to values
        """
        metrics: Dict[str, float] = {}

        # Try to get document-specific metrics
        if hasattr(data, "nlp"):
            nlp = data.nlp
            if hasattr(nlp, "get_tokens"):
                tokens = nlp.get_tokens()
                if tokens:
                    metrics[f"{self.prefix}.token_count"] = float(len(tokens))

            if hasattr(nlp, "get_entities"):
                entities = nlp.get_entities()
                if entities:
                    metrics[f"{self.prefix}.entity_count"] = float(len(entities))

        # Try to get FHIR-specific metrics
        if hasattr(data, "fhir"):
            fhir = data.fhir
            if hasattr(fhir, "problem_list"):
                problem_list = fhir.problem_list
                if problem_list:
                    metrics[f"{self.prefix}.condition_count"] = float(len(problem_list))

        # Try to get model output metrics
        if hasattr(data, "models"):
            models = data.models
            if hasattr(models, "_huggingface_results"):
                hf_results = models._huggingface_results
                if hf_results:
                    metrics[f"{self.prefix}.hf_task_count"] = float(len(hf_results))

            if hasattr(models, "_langchain_results"):
                lc_results = models._langchain_results
                if lc_results:
                    metrics[f"{self.prefix}.lc_task_count"] = float(len(lc_results))

        return metrics

    def reset(self) -> None:
        """Reset the component state for a new run."""
        self._start_time = None
        self._call_count = 0

    def log_pipeline_params(self, params: Dict[str, Any]) -> None:
        """Log pipeline parameters to the active run.

        This is a convenience method for logging pipeline configuration
        parameters that aren't automatically captured.

        Args:
            params: Dictionary of parameter names to values
        """
        if self.tracker.get_run_id() is None:
            logger.warning("No active run, cannot log parameters")
            return

        prefixed_params = {f"{self.prefix}.{k}": v for k, v in params.items()}
        self.tracker.log_params(prefixed_params)


class MLFlowStartRunComponent(BaseComponent[T], Generic[T]):
    """Pipeline component that starts an MLFlow run on first call.

    This component can be placed at the beginning of a pipeline to
    automatically start an MLFlow run when the pipeline is executed.
    The run will remain active until explicitly ended.

    Note:
        This component does NOT automatically end the run. Use in
        combination with MLFlowEndRunComponent or manually end the run.

    Example:
        >>> pipeline = Pipeline[Document]()
        >>> pipeline.add_node(
        ...     MLFlowStartRunComponent(tracker, run_name="inference"),
        ...     position="first"
        ... )
        >>> pipeline.add_node(SpacyNLP.from_model_id("en_core_web_sm"))
        >>> pipeline.add_node(MLFlowEndRunComponent(tracker), position="last")
    """

    def __init__(
        self,
        tracker: "MLFlowTracker",
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize the component.

        Args:
            tracker: MLFlowTracker instance
            run_name: Optional name for the run
            tags: Optional tags for the run
        """
        self.tracker = tracker
        self.run_name = run_name
        self.tags = tags
        self._run_started = False

    def __call__(self, data: DataContainer[T]) -> DataContainer[T]:
        """Start an MLFlow run if not already started.

        Args:
            data: Input data container

        Returns:
            The same data container (pass-through)
        """
        if not self._run_started and self.tracker.get_run_id() is None:
            # Import mlflow for direct run management
            from healthchain.mlflow.tracker import _get_mlflow

            mlflow = _get_mlflow()
            self.tracker._ensure_initialized()
            mlflow.start_run(
                experiment_id=self.tracker._experiment_id,
                run_name=self.run_name,
                tags=self.tags,
            )
            self._run_started = True
            logger.info(f"Started MLFlow run: {self.tracker.get_run_id()}")

        return data


class MLFlowEndRunComponent(BaseComponent[T], Generic[T]):
    """Pipeline component that ends the active MLFlow run.

    This component can be placed at the end of a pipeline to
    automatically end the MLFlow run when the pipeline completes.

    Example:
        >>> pipeline.add_node(MLFlowEndRunComponent(tracker), position="last")
    """

    def __init__(self, tracker: "MLFlowTracker") -> None:
        """Initialize the component.

        Args:
            tracker: MLFlowTracker instance
        """
        self.tracker = tracker

    def __call__(self, data: DataContainer[T]) -> DataContainer[T]:
        """End the active MLFlow run if one exists.

        Args:
            data: Input data container

        Returns:
            The same data container (pass-through)
        """
        if self.tracker.get_run_id() is not None:
            from healthchain.mlflow.tracker import _get_mlflow

            mlflow = _get_mlflow()
            run_id = self.tracker.get_run_id()
            mlflow.end_run()
            self.tracker._active_run = None
            logger.info(f"Ended MLFlow run: {run_id}")

        return data
