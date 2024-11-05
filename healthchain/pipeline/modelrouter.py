from healthchain.pipeline.base import ModelConfig, ModelSource
from healthchain.pipeline.components.base import BaseComponent

from typing import Generic, TypeVar


T = TypeVar("T", bound=BaseComponent)


class ModelRouter(Generic[T]):
    """
    A utility class that creates appropriate components based on model source.
    Maps model sources to initialization functions.

    The ModelRouter handles initialization of different model types (e.g. SpaCy, Hugging Face)
    based on a provided ModelConfig. It abstracts away the specific initialization details
    for each model source and provides a unified interface through get_component().

    Attributes:
        _init_functions (Dict[ModelSource, Callable]): Mapping of model sources to their
            initialization functions

    Examples:
        >>> config = ModelConfig(source=ModelSource.SPACY, model_id="en_core_sci_md")
        >>> router = ModelRouter()
        >>> component = router.get_component(config)

        >>> # With local model path
        >>> config = ModelConfig(
        ...     source=ModelSource.HUGGINGFACE,
        ...     model_id="bert-base",
        ...     path="./models/bert",
        ...     config={"task": "ner"}
        ... )
        >>> component = router.get_component(config)
    """

    def __init__(self):
        """Initialize the ModelRouter with model initialization mapping."""
        self._init_functions = {
            ModelSource.SPACY: self._init_spacy_model,
            ModelSource.HUGGINGFACE: self._init_huggingface_model,
        }

    def get_component(self, config: ModelConfig) -> T:
        """
        Create and return the appropriate component based on model configuration.

        This method takes a ModelConfig object and initializes the corresponding model component
        based on the specified source (e.g. SpaCy, Hugging Face). The config is stored as an
        instance variable to be used by the specific initialization functions.

        Args:
            config (ModelConfig): Configuration object containing:
                - source: The model source (e.g. ModelSource.SPACY)
                - model_id: ID or name of the model
                - path: Optional local path to model files
                - config: Optional dict with additional configuration

        Returns:
            T: An initialized component of the appropriate type (e.g. SpacyComponent,
               HuggingFaceComponent)

        Raises:
            ValueError: If the model source specified in config is not supported
            ImportError: If required dependencies for the model source are not installed
        """
        init_func = self._init_functions.get(config.source)

        if not init_func:
            raise ValueError(f"Unsupported model source: {config.source}")

        self.model_config = config  # Store config for use in init functions
        return init_func()

    def _init_spacy_model(self) -> T:
        """Initialize SpaCy model component.

        Uses the stored model_config to initialize a SpacyComponent with either:
        - A local model from model_config.path if specified
        - A remote/installed model using model_config.model_id

        Returns:
            SpacyComponent: Initialized SpaCy model component

        Raises:
            ImportError: If spacy or required model is not installed
        """
        from healthchain.pipeline.components.integrations import SpacyComponent

        if self.model_config.path is not None:
            return SpacyComponent(model=self.model_config.path)
        return SpacyComponent(model=self.model_config.model_id)

    def _init_huggingface_model(self) -> T:
        """Initialize Hugging Face model component.

        Uses the stored model_config to initialize a HuggingFaceComponent with either:
        - A local model from model_config.path if specified
        - A remote/installed model using model_config.model_id

        The task parameter is extracted from model_config.config if provided.

        Returns:
            HuggingFaceComponent: Initialized Hugging Face model component

        Raises:
            ImportError: If transformers or required model is not installed
        """
        from healthchain.pipeline.components.integrations import HuggingFaceComponent

        if self.model_config.path is not None:
            return HuggingFaceComponent(
                task=self.model_config.config.get("task"), model=self.model_config.path
            )
        return HuggingFaceComponent(
            task=self.model_config.config.get("task"), model=self.model_config.model_id
        )
