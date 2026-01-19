"""Decorators for MLFlow tracking integration."""

import functools
import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, TypeVar

from healthchain.mlflow.config import MLFlowConfig

if TYPE_CHECKING:
    from healthchain.mlflow.tracker import MLFlowTracker

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def track_model(
    experiment: Optional[str] = None,
    run_name: Optional[str] = None,
    tracking_uri: str = "mlruns",
    tags: Optional[Dict[str, str]] = None,
    log_params: Optional[Dict[str, Any]] = None,
    auto_log_time: bool = True,
) -> Callable[[F], F]:
    """Decorator for tracking model inference with MLFlow.

    This decorator wraps a function to automatically create an MLFlow run,
    log execution time, and optionally log parameters and tags. It's designed
    for tracking individual model inference calls.

    Args:
        experiment: Name of the MLFlow experiment. If not specified, uses
            "healthchain-default".
        run_name: Optional name for the run. If not specified, uses the
            function name.
        tracking_uri: URI for the MLFlow tracking server. Defaults to "mlruns".
        tags: Optional tags to add to the run.
        log_params: Optional parameters to log with the run.
        auto_log_time: Whether to automatically log execution time.
            Defaults to True.

    Returns:
        Decorated function that tracks execution with MLFlow.

    Example:
        >>> @track_model(experiment="ner-models")
        ... def run_inference(doc: Document) -> Document:
        ...     return model(doc)
        >>>
        >>> result = run_inference(doc)  # Automatically tracked

        >>> @track_model(
        ...     experiment="clinical-nlp",
        ...     tags={"model": "spacy", "version": "1.0"},
        ...     log_params={"threshold": 0.5}
        ... )
        ... def extract_entities(text: str) -> List[Dict]:
        ...     return nlp(text).ents
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from healthchain.mlflow.tracker import MLFlowTracker

            # Create config and tracker
            config = MLFlowConfig(
                tracking_uri=tracking_uri,
                experiment_name=experiment or "healthchain-default",
                tags=tags or {},
            )
            tracker = MLFlowTracker(config)

            # Determine run name
            actual_run_name = run_name or func.__name__

            # Execute with tracking
            with tracker.start_run(run_name=actual_run_name):
                # Log any specified parameters
                if log_params:
                    tracker.log_params(log_params)

                # Log function metadata
                tracker.log_params(
                    {
                        "function_name": func.__name__,
                        "function_module": func.__module__,
                    }
                )

                # Track execution time
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    if auto_log_time:
                        elapsed = time.time() - start_time
                        tracker.log_metrics({"execution_time_seconds": elapsed})
                    tracker.set_tag("status", "success")
                    return result
                except Exception as e:
                    if auto_log_time:
                        elapsed = time.time() - start_time
                        tracker.log_metrics({"execution_time_seconds": elapsed})
                    tracker.set_tag("status", "failed")
                    tracker.set_tag("error", str(e)[:250])  # Truncate long errors
                    raise

        return wrapper  # type: ignore

    return decorator


def track_pipeline(
    experiment: Optional[str] = None,
    run_name: Optional[str] = None,
    tracking_uri: str = "mlruns",
    tags: Optional[Dict[str, str]] = None,
    log_input_shape: bool = True,
    log_output_shape: bool = True,
) -> Callable[[F], F]:
    """Decorator for tracking pipeline execution with MLFlow.

    This decorator wraps a pipeline function to automatically create an MLFlow
    run and log pipeline-specific metrics like input/output shapes and
    execution time. It's designed for tracking complete pipeline executions.

    Args:
        experiment: Name of the MLFlow experiment. If not specified, uses
            "healthchain-pipelines".
        run_name: Optional name for the run. If not specified, uses the
            function name with "-pipeline" suffix.
        tracking_uri: URI for the MLFlow tracking server. Defaults to "mlruns".
        tags: Optional tags to add to the run.
        log_input_shape: Whether to log input data shape/length.
            Defaults to True.
        log_output_shape: Whether to log output data shape/length.
            Defaults to True.

    Returns:
        Decorated function that tracks pipeline execution with MLFlow.

    Example:
        >>> @track_pipeline(experiment="clinical-pipelines")
        ... def process_documents(docs: List[Document]) -> List[Document]:
        ...     return [pipeline(doc) for doc in docs]
        >>>
        >>> results = process_documents(documents)  # Automatically tracked
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from healthchain.mlflow.tracker import MLFlowTracker

            # Create config and tracker
            config = MLFlowConfig(
                tracking_uri=tracking_uri,
                experiment_name=experiment or "healthchain-pipelines",
                tags=tags or {},
            )
            tracker = MLFlowTracker(config)

            # Determine run name
            actual_run_name = run_name or f"{func.__name__}-pipeline"

            # Execute with tracking
            with tracker.start_run(run_name=actual_run_name):
                # Log function metadata
                tracker.log_params(
                    {
                        "pipeline_name": func.__name__,
                        "pipeline_module": func.__module__,
                    }
                )

                # Log input shape if requested
                if log_input_shape and args:
                    input_metrics = _get_shape_metrics(args[0], "input")
                    if input_metrics:
                        tracker.log_params(input_metrics)

                # Track execution time
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)

                    # Log timing
                    elapsed = time.time() - start_time
                    tracker.log_metrics({"pipeline_execution_seconds": elapsed})

                    # Log output shape if requested
                    if log_output_shape and result is not None:
                        output_metrics = _get_shape_metrics(result, "output")
                        if output_metrics:
                            tracker.log_metrics(
                                {
                                    k: float(v)
                                    for k, v in output_metrics.items()
                                    if isinstance(v, (int, float))
                                }
                            )

                    tracker.set_tag("status", "success")
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    tracker.log_metrics({"pipeline_execution_seconds": elapsed})
                    tracker.set_tag("status", "failed")
                    tracker.set_tag("error", str(e)[:250])
                    raise

        return wrapper  # type: ignore

    return decorator


def _get_shape_metrics(data: Any, prefix: str) -> Dict[str, Any]:
    """Extract shape/length metrics from data.

    Args:
        data: Data to extract metrics from
        prefix: Prefix for metric names

    Returns:
        Dictionary of metric names to values
    """
    metrics: Dict[str, Any] = {}

    # Handle lists/sequences
    if isinstance(data, (list, tuple)):
        metrics[f"{prefix}_count"] = len(data)

    # Handle strings
    elif isinstance(data, str):
        metrics[f"{prefix}_length"] = len(data)

    # Handle DataContainer-like objects
    elif hasattr(data, "text"):
        text = getattr(data, "text", None)
        if text:
            metrics[f"{prefix}_text_length"] = len(text)

    # Handle objects with __len__
    elif hasattr(data, "__len__"):
        try:
            metrics[f"{prefix}_length"] = len(data)
        except TypeError:
            pass

    return metrics


class TrackedPipeline:
    """Wrapper class for tracking pipeline execution with MLFlow.

    This class provides an alternative to decorators for tracking pipeline
    execution. It wraps an existing pipeline and tracks each call.

    Example:
        >>> from healthchain.pipeline import Pipeline
        >>> from healthchain.mlflow import TrackedPipeline, MLFlowConfig
        >>>
        >>> pipeline = Pipeline[Document]()
        >>> pipeline.add_node(SpacyNLP.from_model_id("en_core_web_sm"))
        >>>
        >>> config = MLFlowConfig(experiment_name="clinical-nlp")
        >>> tracked = TrackedPipeline(pipeline, config)
        >>>
        >>> result = tracked(doc)  # Automatically tracked
    """

    def __init__(
        self,
        pipeline: Callable,
        config: Optional[MLFlowConfig] = None,
        run_name_prefix: str = "pipeline-run",
    ) -> None:
        """Initialize the tracked pipeline wrapper.

        Args:
            pipeline: The pipeline to wrap
            config: Optional MLFlowConfig. If not provided, creates a default.
            run_name_prefix: Prefix for run names
        """
        from healthchain.mlflow.tracker import MLFlowTracker

        self.pipeline = pipeline
        self.config = config or MLFlowConfig()
        self.tracker = MLFlowTracker(self.config)
        self.run_name_prefix = run_name_prefix
        self._call_count = 0

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the pipeline with tracking.

        Args:
            *args: Arguments to pass to the pipeline
            **kwargs: Keyword arguments to pass to the pipeline

        Returns:
            Pipeline output
        """
        self._call_count += 1
        run_name = f"{self.run_name_prefix}-{self._call_count}"

        with self.tracker.start_run(run_name=run_name):
            self.tracker.log_params({"call_number": self._call_count})

            start_time = time.time()
            try:
                result = self.pipeline(*args, **kwargs)
                elapsed = time.time() - start_time
                self.tracker.log_metrics({"execution_time_seconds": elapsed})
                self.tracker.set_tag("status", "success")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                self.tracker.log_metrics({"execution_time_seconds": elapsed})
                self.tracker.set_tag("status", "failed")
                self.tracker.set_tag("error", str(e)[:250])
                raise

    def get_tracker(self) -> "MLFlowTracker":
        """Get the underlying MLFlowTracker.

        Returns:
            The MLFlowTracker instance
        """
        return self.tracker
