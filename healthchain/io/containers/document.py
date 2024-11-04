from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from spacy.tokens import Doc as SpacyDoc

from healthchain.io.containers.base import BaseDocument
from healthchain.models.responses import Action, Card
from healthchain.models.data import CcdData, CdsFhirData, ConceptLists
from healthchain.models.data.concept import (
    AllergyConcept,
    MedicationConcept,
    ProblemConcept,
)


@dataclass
class NlpAnnotations:
    """
    Container for NLP-specific annotations and results.

    This class stores various NLP annotations and processing results from text analysis,
    including preprocessed text, tokens, named entities, embeddings and spaCy documents.

    Attributes:
        preprocessed_text (str): The preprocessed version of the input text.
        tokens (List[str]): List of tokenized words/subwords from the text.
        entities (List[Dict[str, Any]]): Named entities extracted from the text,
            containing text spans, labels and character offsets.
        embeddings (Optional[List[float]]): Vector embeddings generated from the text.
        spacy_doc (Optional[SpacyDoc]): The processed spaCy Doc object.

    Methods:
        add_spacy_doc(doc: SpacyDoc): Processes a spaCy Doc to extract tokens and entities.
    """

    preprocessed_text: str = ""
    tokens: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    embeddings: Optional[List[float]] = None
    spacy_doc: Optional[SpacyDoc] = None

    def add_spacy_doc(self, doc: SpacyDoc):
        self.spacy_doc = doc
        self.tokens = [token.text for token in doc]
        self.entities = [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
            for ent in doc.ents
        ]


@dataclass
class ModelOutputs:
    """
    Container for storing and managing third-party integration model outputs.

    This class stores outputs from different NLP/ML frameworks like Hugging Face
    and LangChain, organizing them by task type.

    Attributes:
        huggingface_results (Dict[str, Any]): Dictionary storing Hugging Face model
            outputs, keyed by task name.
        langchain_results (Dict[str, Any]): Dictionary storing LangChain outputs,
            keyed by task name.

    Methods:
        add_huggingface_output(task: str, output: Any): Adds a Hugging Face model
            output for a specific task.
        add_langchain_output(task: str, output: Any): Adds a LangChain output
            for a specific task.
    """

    huggingface_results: Dict[str, Any] = field(default_factory=dict)
    langchain_results: Dict[str, Any] = field(default_factory=dict)

    def add_huggingface_output(self, task: str, output: Any):
        self.huggingface_results[task] = output

    def add_langchain_output(self, task: str, output: Any):
        self.langchain_results[task] = output


@dataclass
class StructuredData:
    """
    Container for structured clinical document formats.

    This class stores and manages structured clinical data in different formats,
    including CCD (Continuity of Care Document) and FHIR (Fast Healthcare
    Interoperability Resources).

    Attributes:
        ccd_data (Optional[CcdData]): Clinical data in CCD format, containing
            problems, medications, allergies and other clinical information.
        fhir_data (Optional[CdsFhirData]): Clinical data in FHIR format for
            clinical decision support.

    Methods:
        update_ccd_from_concepts: Updates the CCD data with new clinical concepts,
            either by overwriting or extending existing data.
    """

    ccd_data: Optional[CcdData] = None
    fhir_data: Optional[CdsFhirData] = None

    def update_ccd_from_concepts(
        self, concepts: ConceptLists, overwrite: bool = False
    ) -> None:
        """
        Updates the CCD data with new clinical concepts.

        This method takes a ConceptLists object containing problems, medications,
        and allergies, and updates the internal CCD data accordingly. If no CCD
        data exists, it creates a new CcdData instance.

        Args:
            concepts (ConceptLists): The new clinical concepts to add, containing
                problems, medications, and allergies lists.
            overwrite (bool, optional): If True, replaces existing concepts.
                If False, extends the existing lists. Defaults to False.

        Returns:
            None
        """
        if self.ccd_data is None:
            self.ccd_data = CcdData()

        if overwrite:
            self.ccd_data.concepts.problems = concepts.problems
            self.ccd_data.concepts.medications = concepts.medications
            self.ccd_data.concepts.allergies = concepts.allergies
        else:
            self.ccd_data.concepts.problems.extend(concepts.problems)
            self.ccd_data.concepts.medications.extend(concepts.medications)
            self.ccd_data.concepts.allergies.extend(concepts.allergies)


@dataclass
class CdsAnnotations:
    """
    Container for Clinical Decision Support (CDS) results.

    This class stores the outputs from clinical decision support systems,
    including CDS Hooks cards and suggested clinical actions.

    Attributes:
        cards (Optional[List[Card]]): A list of CDS Hooks cards containing
            clinical recommendations, warnings, or other decision support content.
        actions (Optional[List[Action]]): A list of suggested clinical actions
            that could be taken based on the CDS analysis.
    """

    cards: Optional[List[Card]] = None
    actions: Optional[List[Action]] = None


@dataclass
class Document(BaseDocument):
    """
    A document container that extends BaseDocument with rich annotation capabilities.

    This class extends DataContainer to specifically handle textual document data.
    It provides functionality to work with raw text, tokenized text, and outputs from
    various NLP libraries like spaCy, Hugging Face, and LangChain.

    This class provides a comprehensive document representation that can include:
    - NLP annotations (tokens, entities, embeddings, spaCy docs)
    - Clinical concepts (problems, medications, allergies)
    - Structured clinical documents (CCD, FHIR)
    - Clinical decision support results (cards, actions)
    - ML model outputs (Hugging Face, LangChain)

    The Document class serves as the main data structure passed through the pipeline,
    accumulating annotations and analysis results at each step.

    Attributes:
        nlp (NlpAnnotations): Container for NLP-related annotations
        concepts (ConceptLists): Container for extracted medical concepts
        structured_docs (StructuredData): Container for structured clinical documents
        cds (CdsAnnotations): Container for clinical decision support results
        model_outputs (ModelOutputs): Container for ML model outputs

    Inherits from:
        BaseDocument: Provides base document functionality and raw text storage
    """

    nlp: NlpAnnotations = field(default_factory=NlpAnnotations)
    concepts: ConceptLists = field(default_factory=ConceptLists)
    structured_docs: StructuredData = field(default_factory=StructuredData)
    cds: CdsAnnotations = field(default_factory=CdsAnnotations)
    model_outputs: ModelOutputs = field(default_factory=ModelOutputs)

    def add_concepts(
        self,
        problems: List[ProblemConcept] = None,
        medications: List[MedicationConcept] = None,
        allergies: List[AllergyConcept] = None,
    ):
        """
        Add extracted medical concepts to the document.

        This method adds medical concepts (problems, medications, allergies) to their
        respective lists in the document's concepts container. Each concept type is
        optional and will only be added if provided.

        Args:
            problems (List[ProblemConcept], optional): List of medical problems/conditions
                to add to the document. Defaults to None.
            medications (List[MedicationConcept], optional): List of medications
                to add to the document. Defaults to None.
            allergies (List[AllergyConcept], optional): List of allergies
                to add to the document. Defaults to None.

        Example:
            >>> doc.add_concepts(
            ...     problems=[ProblemConcept(display_name="Hypertension")],
            ...     medications=[MedicationConcept(display_name="Aspirin")]
            ... )
        """
        if problems:
            self.concepts.problems.extend(problems)
        if medications:
            self.concepts.medications.extend(medications)
        if allergies:
            self.concepts.allergies.extend(allergies)

    def generate_ccd(self, overwrite: bool = False) -> CcdData:
        """
        Generate a CCD (Continuity of Care Document) from the current medical concepts.

        This method creates or updates a CCD in the structured_docs container using the
        medical concepts (problems, medications, allergies) currently stored in the document.
        The CCD is a standard format for exchanging clinical information.

        Args:
            overwrite (bool, optional): If True, overwrites any existing CCD data.
                If False, merges with existing CCD data. Defaults to False.

        Returns:
            CcdData: The generated CCD data.

        Example:
            >>> doc.add_concepts(problems=[ProblemConcept(display_name="Hypertension")])
            >>> doc.generate_ccd()  # Creates CCD with the hypertension problem
        """
        self.structured_docs.update_ccd_from_concepts(self.concepts, overwrite)

        return self.structured_docs.ccd_data

    def __post_init__(self):
        """Initialize the document with basic tokenization if needed."""
        super().__post_init__()
        self.text = self.data
        if not self.nlp.tokens:
            self.nlp.tokens = self.text.split()  # Basic tokenization if not provided

    # Convenience methods to delegate to the appropriate container
    def add_spacy_doc(self, doc: SpacyDoc):
        """
        Add a spaCy Doc object to the document and update the base text.

        This method adds a spaCy Doc object to the document's NLP container and updates
        the document's base text to match the spaCy Doc text.

        Args:
            doc (SpacyDoc): The spaCy Doc object to add to the document.

        Example:
            >>> import spacy
            >>> nlp = spacy.load("en_core_web_sm")
            >>> spacy_doc = nlp("Patient has hypertension")
            >>> doc.add_spacy_doc(spacy_doc)
        """
        self.nlp.add_spacy_doc(doc)
        self.text = doc.text  # Update base text if needed

    def get_spacy_doc(self) -> Optional[SpacyDoc]:
        """
        Get the spaCy Doc object from the document's NLP container.
        """
        return self.nlp.spacy_doc

    def add_huggingface_output(self, task: str, output: Any):
        """
        Add a Hugging Face model output to the document's model outputs container.
        """
        self.model_outputs.add_huggingface_output(task, output)

    def get_huggingface_output(self, task: str) -> Any:
        """
        Get a Hugging Face model output from the document's model outputs container.
        """
        return self.model_outputs.huggingface_results.get(task)

    def add_langchain_output(self, task: str, output: Any):
        """
        Add a LangChain model output to the document's model outputs container.
        """
        self.model_outputs.add_langchain_output(task, output)

    def get_langchain_output(self, task: str) -> Any:
        """
        Get a LangChain model output from the document's model outputs container.
        """
        return self.model_outputs.langchain_results.get(task)

    def get_tokens(self) -> List[str]:
        """
        Get the list of tokens from the document's text. Defaults to .split() if tokenizer not provided.
        """
        return self.nlp.tokens

    def get_entities(self) -> List[Dict[str, Any]]:
        """
        Get the list of entities from the document's text.
        """
        return self.nlp.entities

    def set_entities(self, entities: List[Dict[str, Any]]):
        """
        Set the list of entities in the document's text.
        """
        self.nlp.entities = entities

    def get_embeddings(self) -> Optional[List[float]]:
        """
        Get the list of embeddings from the document's text.
        """
        return self.nlp.embeddings

    def set_embeddings(self, embeddings: List[float]):
        """
        Set the list of embeddings in the document's text.
        """
        self.nlp.embeddings = embeddings

    def get_fhir_data(self) -> Optional[CdsFhirData]:
        """
        Get the FHIR data from the document's structured_docs container.
        """
        return self.structured_docs.fhir_data

    def word_count(self) -> int:
        """
        Get the word count from the document's text.
        """
        return len(self.nlp.tokens)

    def __iter__(self) -> Iterator[str]:
        return iter(self.nlp.tokens)

    def __len__(self) -> int:
        return len(self.text)
