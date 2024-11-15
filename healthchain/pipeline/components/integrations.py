from typing import Any, Callable, TypeVar
from spacy.tokens import Doc as SpacyDoc
from spacy.language import Language
from functools import wraps

from healthchain.io.containers import Document
from healthchain.pipeline.components.base import BaseComponent
from healthchain.models.data import ProblemConcept

T = TypeVar("T")


def requires_package(package_name: str, import_path: str) -> Callable:
    """Decorator to check if an optional package is available.

    Args:
        package_name: Name of the package to install (e.g., 'langchain-core')
        import_path: Import path to check (e.g., 'langchain_core.runnables')
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                __import__(import_path)
            except ImportError:
                raise ImportError(
                    f"This feature requires {package_name}. "
                    f"Please install it with: `pip install {package_name}`"
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


class SpacyNLP(BaseComponent[str]):
    """
    A component that integrates spaCy models into the pipeline.

    This component allows using any spaCy model within the pipeline by loading
    and applying it to process text documents. The spaCy doc outputs are stored
    in the document's nlp annotations container under .spacy_docs.

    Args:
        nlp: A pre-configured spaCy Language object.

    Example:
        >>> # Using pre-configured pipeline
        >>> import spacy
        >>> nlp = spacy.load("en_core_web_sm", disable=["parser"])
        >>> component = SpacyNLP(nlp)
        >>> doc = component(doc)
        >>>
        >>> # Or using model name
        >>> component = SpacyNLP.from_model_id("en_core_web_sm", disable=["parser"])
        >>> doc = component(doc)
    """

    def __init__(self, nlp: "Language"):
        """Initialize with a pre-configured spaCy Language object."""
        self._nlp = nlp

    @classmethod
    def from_model_id(cls, model: str, **kwargs: Any) -> "SpacyNLP":
        """
        Create a SpacyNLP component from a model identifier.

        Args:
            model (str): The name or path of the spaCy model to load.
                Can be a model name like 'en_core_web_sm' or path to saved model.
            **kwargs: Additional configuration options passed to spacy.load.
                Common options include disable, exclude, enable.

        Returns:
            SpacyNLP: Initialized spaCy component

        Raises:
            ImportError: If spaCy or the specified model is not installed
            TypeError: If invalid kwargs are passed to spacy.load
        """
        try:
            import spacy
        except ImportError:
            raise ImportError(
                "Could not import spacy. Please install it with: " "`pip install spacy`"
            )

        try:
            nlp = spacy.load(model, **kwargs)
        except TypeError as e:
            raise TypeError(f"Invalid kwargs for spacy.load: {str(e)}")
        except Exception as e:
            raise ImportError(
                f"Could not load spaCy model {model}! "
                "Make sure you have installed it with: "
                f"`python -m spacy download {model}`"
            ) from e

        return cls(nlp)

    def _add_concepts_to_hc_doc(self, spacy_doc: SpacyDoc, hc_doc: Document):
        """
        Extract entities from spaCy Doc and add them to the HealthChain Document concepts.

        Args:
            spacy_doc (Doc): The processed spaCy Doc object containing entities
            hc_doc (Document): The HealthChain Document to store concepts in

        Note: Defaults to ProblemConcepts and SNOMED CT concepts
        # TODO: make configurable
        """
        concepts = []
        for ent in spacy_doc.ents:
            # Check for CUI attribute from extensions like medcat
            concept = ProblemConcept(
                code=ent._.cui if hasattr(ent, "_.cui") else None,
                code_system="2.16.840.1.113883.6.96",
                code_system_name="SNOMED CT",
                display_name=ent.text,
            )
            concepts.append(concept)

        # Add to document concepts
        hc_doc.add_concepts(problems=concepts)

    def __call__(self, doc: Document) -> Document:
        """Process the document using the spaCy pipeline. Adds outputs to nlp.spacy_docs."""
        spacy_doc = self._nlp(doc.data)
        self._add_concepts_to_hc_doc(spacy_doc, doc)
        doc.nlp.add_spacy_doc(spacy_doc)
        return doc


class HFTransformer(BaseComponent[str]):
    """
    A component that integrates Hugging Face transformers models into the pipeline.

    This component allows using any Hugging Face model and task within the pipeline
    by wrapping the transformers.pipeline API. The model outputs are stored in the
    document's model_outputs container under the "huggingface" source key.

    Note that this component is only recommended for non-conversational language tasks.
    For chat-based tasks, consider using LangChainLLM instead.

    Args:
        pipeline (Any): A pre-configured HuggingFace pipeline object to use for inference.
            Must be an instance of transformers.pipelines.base.Pipeline.

    Attributes:
        task (str): The task name of the underlying pipeline, e.g. "sentiment-analysis", "ner".
            Automatically extracted from the pipeline object.

    Raises:
        ImportError: If the transformers package is not installed
        TypeError: If pipeline is not a valid HuggingFace Pipeline instance

    Example:
        >>> # Initialize for sentiment analysis
        >>> from transformers import pipeline
        >>> nlp = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
        >>> component = HFTransformer(pipeline=nlp)
        >>> doc = component(doc)  # Analyzes sentiment of doc.data
        >>>
        >>> # Or use the factory method
        >>> component = HFTransformer.from_model_id(
        ...     model="facebook/bart-large-cnn",
        ...     task="summarization",
        ...     max_length=130,
        ...     min_length=30,
        ...     do_sample=False
        ... )
        >>> doc = component(doc)  # Generates summary of doc.data
    """

    @requires_package("transformers", "transformers.pipelines")
    def __init__(self, pipeline: Any):
        """Initialize with a pre-configured HuggingFace pipeline.

        Args:
            pipeline: A pre-configured HuggingFace pipeline object from transformers.pipeline().
                     Must be an instance of transformers.pipelines.base.Pipeline.

        Raises:
            ImportError: If transformers package is not installed
            TypeError: If pipeline is not a valid HuggingFace Pipeline instance
        """
        from transformers.pipelines.base import Pipeline

        if not isinstance(pipeline, Pipeline):
            raise TypeError(
                f"Expected HuggingFace Pipeline object, got {type(pipeline)}"
            )
        self._pipe = pipeline
        self.task = pipeline.task

    @classmethod
    @requires_package("transformers", "transformers.pipelines")
    def from_model_id(cls, model: str, task: str, **kwargs: Any) -> "HFTransformer":
        """Create a transformer component from a model identifier.

        Factory method that initializes a HuggingFace pipeline with the specified model and task,
        then wraps it in a HFTransformer component.

        Args:
            model: The model identifier or path to load. Can be:
                - A model ID from the HuggingFace Hub (e.g. "bert-base-uncased")
                - A local path to a saved model
            task: The task to run (e.g. "text-classification", "token-classification", "summarization")
            **kwargs: Additional configuration options passed to transformers.pipeline()
                Common options include:
                - device: Device to run on ("cpu", "cuda", etc.)
                - batch_size: Batch size for inference
                - model_kwargs: Dict of model-specific args

        Returns:
            HFTransformer: Initialized transformer component wrapping the pipeline

        Raises:
            TypeError: If invalid kwargs are passed to pipeline initialization
            ValueError: If pipeline initialization fails for any other reason
            ImportError: If transformers package is not installed
        """
        from transformers import pipeline

        try:
            pipe = pipeline(task=task, model=model, **kwargs)
        except TypeError as e:
            raise TypeError(f"Invalid kwargs for transformers.pipeline: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error initializing transformer pipeline: {str(e)}")

        return cls(pipeline=pipe)

    def __call__(self, doc: Document) -> Document:
        """Process the document using the Hugging Face pipeline. Adds outputs to .model_outputs['huggingface']."""
        output = self._pipe(doc.data)
        doc.models.add_output("huggingface", self.task, output)

        return doc


class LangChainLLM(BaseComponent[str]):
    """
    A component that integrates LangChain chains into the pipeline.

    This component allows using any LangChain chain within the pipeline by wrapping
    the chain's invoke method. The chain outputs are stored in the document's
    model_outputs container under the "langchain" source key.

    Args:
        chain (Runnable): The LangChain chain to run on the document text.
            Must be a Runnable object from the LangChain library.
        task (str): The task name to use when storing outputs, e.g. "summarization", "chat".
            Used as key to organize model outputs in the document's model container.
        **kwargs: Additional parameters to pass to the chain's invoke method.
            These are forwarded directly to the chain's invoke() call.

    Raises:
        TypeError: If chain is not a LangChain Runnable object or if invalid kwargs are passed
        ValueError: If there is an error during chain invocation
        ImportError: If langchain-core package is not installed

    Example:
        >>> from langchain_core.prompts import ChatPromptTemplate
        >>> from langchain_openai import ChatOpenAI

        >>> chain = ChatPromptTemplate.from_template("What is {input}?") | ChatOpenAI()
        >>> component = LangChainLLM(chain=chain, task="chat")
        >>> doc = component(doc)  # Runs the chain on doc.data and stores output
    """

    @requires_package("langchain-core", "langchain_core.runnables")
    def __init__(self, chain: Any, task: str, **kwargs: Any):
        """Initialize with a LangChain chain."""
        from langchain_core.runnables import Runnable

        if not isinstance(chain, Runnable):
            raise TypeError(f"Expected LangChain Runnable object, got {type(chain)}")

        self.chain = chain
        self.task = task
        self.kwargs = kwargs

    def __call__(self, doc: Document) -> Document:
        """Process the document using the LangChain chain. Adds outputs to .model_outputs['langchain']."""
        try:
            output = self.chain.invoke(doc.data, **self.kwargs)
        except TypeError as e:
            raise TypeError(f"Invalid kwargs for chain.invoke: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error during chain invocation: {str(e)}")

        doc.models.add_output("langchain", self.task, output)

        return doc
