from typing import Generic, TypeVar

from healthchain.pipeline.basepipeline import Pipeline


T = TypeVar("T")


class GenericPipeline(Pipeline, Generic[T]):
    """
    Default Pipeline class for creating a basic data processing pipeline.
    This class inherits from BasePipeline and provides a default implementation
    of the configure_pipeline method, which does not add any specific components.
    """

    def configure_pipeline(self, model_path: str) -> None:
        """
        Configures the pipeline by adding components based on the provided model path.
        This default implementation does not add any specific components.

        Args:
            model_path (str): The path to the model used for configuring the pipeline.
        """
        # Default implementation: No specific components added
        pass
