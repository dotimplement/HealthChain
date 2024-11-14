from healthchain.pipeline.base import ModelConfig, ModelSource
from healthchain.pipeline.components.base import BaseComponent

from typing import Generic, TypeVar


T = TypeVar("T", bound=BaseComponent)


class ModelRouter(Generic[T]):
    """
    A utility class used in prebuilt pipelines that creates appropriate components based on model source.
    Maps model sources to initialization functions.

    The ModelRouter handles initialization of different model types (e.g. SpaCy, Hugging Face, LangChain)
    based on a provided ModelConfig. It abstracts away the specific initialization details
    for each model source and provides a unified interface through get_component().

    The router supports three main model sources:
    - SpaCy: For NLP tasks like NER, dependency parsing etc.
    - Hugging Face: For transformer-based models and tasks
    - LangChain: For LLM chains and chat-based tasks

    Attributes:
        _init_functions (Dict[ModelSource, Callable]): Mapping of model sources to their
            initialization functions
        model_config (ModelConfig): Currently active model configuration

    Examples:
        >>> # Initialize SpaCy model
        >>> config = ModelConfig(
        ...     source=ModelSource.SPACY,
        ...     model="en_core_sci_md",
        ...     kwargs={"disable": ["parser"]}
        ... )
        >>> router = ModelRouter()
        >>> spacy_component = router.get_component(config)

        >>> # Initialize Hugging Face model
        >>> config = ModelConfig(
        ...     source=ModelSource.HUGGINGFACE,
        ...     model="bert-base-uncased",
        ...     task="text-classification",
        ...     kwargs={"device": "cuda"}
        ... )
        >>> hf_component = router.get_component(config)

        >>> # Initialize LangChain model
        >>> from langchain_core.prompts import ChatPromptTemplate
        >>> from langchain_openai import ChatOpenAI
        >>> chain = ChatPromptTemplate.from_template("What is {input}?") | ChatOpenAI()
        >>> config = ModelConfig(
        ...     source=ModelSource.LANGCHAIN,
        ...     model=chain,
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
                - model: Model identifier, path, or LangChain chain instance
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
        """Initialize SpaCy model component.

        Uses the stored model_config to initialize a SpacyNLP with either:
        - A local model from model_config.path if specified
        - A remote/installed model using model_config.model_id

        Returns:
            SpacyNLP: Initialized SpaCy model component

        Raises:
            ImportError: If spacy or required model is not installed
        """
        from healthchain.pipeline.components.integrations import SpacyNLP

        if self.model_config.path is not None:
            return SpacyNLP(model=self.model_config.path, **self.model_config.kwargs)

        return SpacyNLP(model=self.model_config.model, **self.model_config.kwargs)

    def _init_huggingface_model(self) -> T:
        """Initialize Hugging Face model component.

        Uses the stored model_config to initialize a HFTransformer with either:
        - A local model from model_config.path if specified
        - A remote/installed model using model_config.model_id

        The task parameter is extracted from model_config.config if provided.

        Returns:
            HFTransformer: Initialized Hugging Face model component

        Raises:
            ImportError: If transformers or required model is not installed
        """
        from healthchain.pipeline.components.integrations import HFTransformer

        if self.model_config.path is not None:
            return HFTransformer(
                model=self.model_config.path,
                task=self.model_config.task,
                **self.model_config.kwargs,
            )
        return HFTransformer(
            model=self.model_config.model,
            task=self.model_config.task,
            **self.model_config.kwargs,
        )

    def _init_langchain_model(self) -> T:
        """Initialize LangChain model component."""
        from healthchain.pipeline.components.integrations import LangChainLLM

        return LangChainLLM(
            chain=self.model_config.model,
            task=self.model_config.task,
            **self.model_config.kwargs,
        )
