from healthchain.io.containers import Document
from healthchain.pipeline.components.base import BaseComponent
from healthchain.models.data import ProblemConcept
from spacy.tokens import Doc


class SpacyComponent(BaseComponent[str]):
    """
    A component that integrates spaCy models into the pipeline.

    This component allows using any spaCy model within the pipeline by loading
    and applying it to process text documents. The spaCy doc outputs are stored
    in the document's nlp annotations container.

    Args:
        path_to_pipeline (str): The path or name of the spaCy model to load.
            Can be a model name like 'en_core_web_sm' or path to saved model.

    Raises:
        ImportError: If spaCy or the specified model is not installed.

    Example:
        >>> component = SpacyComponent("en_core_web_sm")
        >>> doc = component(doc)  # Processes doc.data with spaCy
    """

    def __init__(self, path_to_pipeline: str):
        # TODO: might need to store model specific info
        import spacy

        try:
            nlp = spacy.load(path_to_pipeline)
        except Exception as e:
            raise ImportError(
                f"Could not load spaCy model {path_to_pipeline}! "
                "Make sure you have installed it with: "
                "`pip install spacy` or `python -m spacy download {model_name}`"
            ) from e
        self.nlp = nlp

    def _add_concepts_to_hc_doc(self, spacy_doc: Doc, hc_doc: Document):
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
                code=ent._.cui if hasattr(ent, "_cui") else None,
                code_system="2.16.840.1.113883.6.96",
                code_system_name="SNOMED CT",
                display_name=ent.text,
            )
            concepts.append(concept)

        # Add to document concepts
        hc_doc.add_concepts(problems=concepts)

    def __call__(self, doc: Document) -> Document:
        spacy_doc = self.nlp(doc.data)
        self._add_concepts_to_hc_doc(spacy_doc, doc)
        doc.nlp.add_spacy_doc(spacy_doc)

        return doc


class HuggingFaceComponent(BaseComponent[str]):
    """
    A component that integrates Hugging Face transformers models into the pipeline.

    This component allows using any Hugging Face model and task within the pipeline
    by wrapping the transformers.pipeline API. The model outputs are stored in the
    document's model_outputs container.

    Args:
        task (str): The task to run, e.g. "sentiment-analysis", "ner", etc.
            Must be a valid task supported by the Hugging Face pipeline API.
        model (str): The model identifier or path to use for the task.
            Can be a model ID from the Hugging Face Hub or a local path.

    Raises:
        ImportError: If the transformers package is not installed.

    Example:
        >>> component = HuggingFaceComponent(
        ...     task="sentiment-analysis",
        ...     model="distilbert-base-uncased-finetuned-sst-2-english"
        ... )
        >>> doc = component(doc)  # Runs sentiment analysis on doc.data
    """

    def __init__(self, task, model):
        try:
            from transformers import pipeline
        except ImportError:
            raise ImportError(
                "Could not import transformers. Please install it with: "
                "`pip install transformers`"
            )

        nlp = pipeline(task=task, model=model)
        self.nlp = nlp
        self.task = task

    def __call__(self, doc: Document) -> Document:
        output = self.nlp(doc.data)
        doc.add_output("huggingface", self.task, output)
        return doc


class LangChainComponent(BaseComponent[str]):
    """
    A component that integrates LangChain chains into the pipeline.

    This component allows using any LangChain chain within the pipeline by wrapping
    the chain's invoke method. The chain outputs are stored in the document's
    model_outputs container.

    Args:
        chain: The LangChain chain to run on the document text.
            Can be any chain object from the LangChain library.

    Example:
        >>> from langchain.chains import LLMChain
        >>> chain = LLMChain(llm=llm, prompt=prompt)
        >>> component = LangChainComponent(chain=chain)
        >>> doc = component(doc)  # Runs the chain on doc.data
    """

    def __init__(self, chain):
        self.chain = chain

    def __call__(self, doc: Document) -> Document:
        output = self.chain.invoke(doc.data)
        doc.models.add_output("langchain", "chain_output", output)
        return doc
