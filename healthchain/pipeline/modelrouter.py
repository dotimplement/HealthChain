from healthchain.pipeline.base import ModelConfig, ModelSource
from healthchain.pipeline.components.base import BaseComponent

from typing import Generic, TypeVar


T = TypeVar("T", bound=BaseComponent)


class ModelRouter(Generic[T]):
    """
    A utility class that creates appropriate model components based on configuration.

    The ModelRouter handles initialization of different model types (SpaCy, Hugging Face, LangChain)
    based on a provided ModelConfig. It abstracts away the specific initialization details
    for each model source and provides a unified interface through get_component().

    Supported model sources:
    - SpaCy: For NLP tasks like NER, dependency parsing etc.
    - Hugging Face: For transformer-based models and tasks
    - LangChain: For LLM chains and chat-based tasks

    Attributes:
        _init_functions (Dict[ModelSource, Callable]): Maps model sources to initialization functions
        model_config (ModelConfig): Currently active model configuration

    Examples:
        >>> # SpaCy model
        >>> config = ModelConfig(
        ...     source=ModelSource.SPACY,
        ...     model_id="en_core_sci_md",
        ...     kwargs={"disable": ["parser"]}
        ... )
        >>> router = ModelRouter()
        >>> spacy_component = router.get_component(config)

        >>> # Hugging Face model
        >>> config = ModelConfig(
        ...     source=ModelSource.HUGGINGFACE,
        ...     model_id="bert-base-uncased",
        ...     task="text-classification",
        ...     kwargs={"device": "cuda"}
        ... )
        >>> hf_component = router.get_component(config)

        >>> # LangChain model
        >>> from langchain_core.prompts import ChatPromptTemplate
        >>> from langchain_openai import ChatOpenAI
        >>> chain = ChatPromptTemplate.from_template("What is {input}?") | ChatOpenAI()
        >>> config = ModelConfig(
        ...     source=ModelSource.LANGCHAIN,
        ...     pipeline_object=chain,
        ...     task="chat",
        ...     kwargs={"temperature": 0.7}
        ... )
        >>> lc_component = router.get_component(config)
    """

    def __init__(self):
        """Initialize the ModelRouter with model initialization mapping."""
        self._init_functions = {
            ModelSource.SPACY: self._init_spacy_model,
            ModelSource.HUGGINGFACE: self._init_huggingface_model,
            ModelSource.LANGCHAIN: self._init_langchain_model,
        }

    def get_component(self, config: ModelConfig) -> T:
        """
        Create and return the appropriate component based on model configuration.

        This method takes a ModelConfig object and initializes the corresponding model component
        based on the specified source (e.g. SpaCy, Hugging Face, LangChain). The config is stored
        as an instance variable to be used by the specific initialization functions.

        Args:
            config (ModelConfig): Configuration object containing:
                - source: The model source (e.g. ModelSource.SPACY, ModelSource.HUGGINGFACE)
                - model_id: Model identifier for pre-trained models
                - pipeline_object: Optional pre-initialized model/chain instance
                - task: Optional task name for the model (e.g. "ner", "text-classification")
                - path: Optional local path to model files
                - kwargs: Optional dict with additional configuration parameters

        Returns:
            T: An initialized component of the appropriate type (SpacyNLP, HFTransformer,
               or LangChainLLM)

        Raises:
            ValueError: If the model source specified in config is not supported
            ImportError: If required dependencies for the model source are not installed
            TypeError: If invalid kwargs are passed to component initialization
        """
        init_func = self._init_functions.get(config.source)

        if not init_func:
            raise ValueError(f"Unsupported model source: {config.source}")

        self.model_config = config  # Store config for use in init functions
        return init_func()

    def _init_spacy_model(self) -> T:
        """Initialize SpaCy model component."""

        from healthchain.pipeline.components.integrations import SpacyNLP

        if self.model_config.path is not None:
            return SpacyNLP.from_model_id(
                model=self.model_config.path, **self.model_config.kwargs
            )

        return SpacyNLP.from_model_id(
            model=self.model_config.model_id, **self.model_config.kwargs
        )

    def _init_huggingface_model(self) -> T:
        """Initialize Hugging Face model component."""

        from healthchain.pipeline.components.integrations import HFTransformer

        if self.model_config.path is not None:
            return HFTransformer.from_model_id(
                model=self.model_config.path,
                task=self.model_config.task,
                **self.model_config.kwargs,
            )
        if self.model_config.pipeline_object is not None:
            return HFTransformer(pipeline=self.model_config.pipeline_object)

        return HFTransformer.from_model_id(
            model=self.model_config.model_id,
            task=self.model_config.task,
            **self.model_config.kwargs,
        )

    def _init_langchain_model(self) -> T:
        """Initialize LangChain model component."""

        from healthchain.pipeline.components.integrations import LangChainLLM

        return LangChainLLM(
            chain=self.model_config.pipeline_object,
            task=self.model_config.task,
            **self.model_config.kwargs,
        )
