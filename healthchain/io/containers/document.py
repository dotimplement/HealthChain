import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Union

from spacy.tokens import Doc as SpacyDoc

from healthchain.io.containers.base import BaseDocument
from healthchain.models.responses import Action, Card
from healthchain.models.data import CcdData, CdsFhirData, ConceptLists
from healthchain.models.data.concept import (
    AllergyConcept,
    MedicationConcept,
    ProblemConcept,
)

logger = logging.getLogger(__name__)


@dataclass
class NlpAnnotations:
    """
    Container for NLP-specific annotations and results.

    This class stores various NLP annotations and processing results from text analysis,
    including preprocessed text, tokens, named entities, embeddings and spaCy documents.

    Attributes:
        _preprocessed_text (str): The preprocessed version of the input text.
        _tokens (List[str]): List of tokenized words from the text.
        _entities (List[Dict[str, Any]]): Named entities extracted from the text, with their labels and positions.
        _embeddings (Optional[List[float]]): Vector embeddings generated from the text.
        _spacy_doc (Optional[SpacyDoc]): The processed spaCy Doc object.

    Methods:
        add_spacy_doc(doc: SpacyDoc): Processes a spaCy Doc to extract tokens and entities.
        get_spacy_doc() -> Optional[SpacyDoc]: Returns the stored spaCy Doc object.
        get_tokens() -> List[str]: Returns the list of tokens.
        set_tokens(tokens: List[str]): Sets the token list.
        set_entities(entities: List[Dict[str, Any]]): Sets the named entities list.
        get_entities() -> List[Dict[str, Any]]: Returns the list of named entities.
        get_embeddings() -> Optional[List[float]]: Returns the vector embeddings.
        set_embeddings(embeddings: List[float]): Sets the vector embeddings.
    """

    _preprocessed_text: str = ""
    _tokens: List[str] = field(default_factory=list)
    _entities: List[Dict[str, Any]] = field(default_factory=list)
    _embeddings: Optional[List[float]] = None
    _spacy_doc: Optional[SpacyDoc] = None

    def add_spacy_doc(self, doc: SpacyDoc):
        self._spacy_doc = doc
        self._tokens = [token.text for token in doc]
        self._entities = [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
            for ent in doc.ents
        ]

    def get_spacy_doc(self) -> Optional[SpacyDoc]:
        return self._spacy_doc

    def get_tokens(self) -> List[str]:
        return self._tokens

    def set_tokens(self, tokens: List[str]):
        self._tokens = tokens

    def set_entities(self, entities: List[Dict[str, Any]]):
        self._entities = entities

    def get_entities(self) -> List[Dict[str, Any]]:
        return self._entities

    def get_embeddings(self) -> Optional[List[float]]:
        return self._embeddings

    def set_embeddings(self, embeddings: List[float]):
        self._embeddings = embeddings


@dataclass
class ModelOutputs:
    """
    Container for storing and managing third-party integration model outputs.

    This class stores outputs from different NLP/ML frameworks like Hugging Face
    and LangChain, organizing them by task type. It also maintains a list of
    generated text outputs across frameworks.

    Attributes:
        _huggingface_results (Dict[str, Any]): Dictionary storing Hugging Face model
            outputs, keyed by task name.
        _langchain_results (Dict[str, Any]): Dictionary storing LangChain outputs,
            keyed by task name.

    Methods:
        add_output(source: str, task: str, output: Any): Adds a model output for a
            specific source and task. For text generation tasks, also extracts and
            stores the generated text.
        get_output(source: str, task: str, default: Any = None) -> Any: Gets the model
            output for a specific source and task. Returns default if not found.
        get_generated_text() -> List[str]: Returns the list of generated text outputs
    """

    _huggingface_results: Dict[str, Any] = field(default_factory=dict)
    _langchain_results: Dict[str, Any] = field(default_factory=dict)

    def add_output(self, source: str, task: str, output: Any):
        if source == "huggingface":
            self._huggingface_results[task] = output
        elif source == "langchain":
            self._langchain_results[task] = output
        else:
            raise ValueError(f"Unknown source: {source}")

    def get_output(self, source: str, task: str) -> Any:
        if source == "huggingface":
            return self._huggingface_results.get(task, {})
        elif source == "langchain":
            return self._langchain_results.get(task, {})
        raise ValueError(f"Unknown source: {source}")

    def get_generated_text(self, source: str, task: str) -> List[str]:
        """
        Returns generated text outputs for a given source and task.

        Handles different output formats for Hugging Face and LangChain. For
        Hugging Face, it extracts the last message content from chat-style
        outputs and common keys like "generated_text", "summary_text", and
        "translation". For LangChain, it converts JSON outputs to strings, and returns
        the output as is if it is already a string.

        Args:
            source (str): Framework name (e.g., "huggingface", "langchain").
            task (str): Task name for retrieving generated text.

        Returns:
            List[str]: List of generated text outputs, or an empty list if none.
        """
        generated_text = []

        if source == "huggingface":
            # Handle chat-style output format
            output = self._huggingface_results.get(task)
            if isinstance(output, list):
                for entry in output:
                    text = entry.get("generated_text")
                    if isinstance(text, list):
                        last_msg = text[-1]
                        if isinstance(last_msg, dict) and "content" in last_msg:
                            generated_text.append(last_msg["content"])
                    # Otherwise get common huggingface output keys
                    elif any(
                        key in entry
                        for key in ["generated_text", "summary_text", "translation"]
                    ):
                        generated_text.append(
                            text
                            or entry.get("summary_text")
                            or entry.get("translation")
                        )
            else:
                logger.warning("HuggingFace output is not a list of dictionaries. ")
        elif source == "langchain":
            output = self._langchain_results.get(task)
            # Check if output is a string
            if isinstance(output, str):
                generated_text.append(output)
            # Try to convert JSON to string
            elif isinstance(output, dict):
                try:
                    import json

                    output_str = json.dumps(output)
                    generated_text.append(output_str)
                except Exception:
                    logger.warning(
                        "LangChain output is not a string and could not be converted to JSON string. "
                        "Chains should output either a string or a JSON object."
                    )
            else:
                logger.warning(
                    "LangChain output is not a string. Chains should output either a string or a JSON object."
                )

        return generated_text


@dataclass
class HL7Data:
    """
    Container for structured clinical document formats.

    This class stores and manages structured clinical data in different formats,
    including CCD (Continuity of Care Document) and FHIR (Fast Healthcare
    Interoperability Resources).

    Attributes:
        _ccd_data (Optional[CcdData]): Clinical data in CCD format, containing
            problems, medications, allergies and other clinical information.
        _fhir_data (Optional[CdsFhirData]): Clinical data in FHIR format for
            clinical decision support.

    Methods:
        update_ccd_from_concepts(concepts: ConceptLists, overwrite: bool = False) -> CcdData:
            Updates the CCD data with new clinical concepts, either by overwriting or extending
            existing data.
        get_fhir_data() -> Optional[CdsFhirData]:
            Returns the FHIR format clinical data if it exists, otherwise None.
        get_ccd_data() -> Optional[CcdData]:
            Returns the CCD format clinical data if it exists, otherwise None.
    """

    _ccd_data: Optional[CcdData] = None
    _fhir_data: Optional[CdsFhirData] = None

    def update_ccd_from_concepts(
        self, concepts: ConceptLists, overwrite: bool = False
    ) -> CcdData:
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
            CcdData: The updated CCD data.
        """
        if self._ccd_data is None:
            self._ccd_data = CcdData()

        if overwrite:
            self._ccd_data.concepts.problems = concepts.problems
            self._ccd_data.concepts.medications = concepts.medications
            self._ccd_data.concepts.allergies = concepts.allergies
        else:
            self._ccd_data.concepts.problems.extend(concepts.problems)
            self._ccd_data.concepts.medications.extend(concepts.medications)
            self._ccd_data.concepts.allergies.extend(concepts.allergies)

        return self._ccd_data

    def get_fhir_data(self) -> Optional[CdsFhirData]:
        return self._fhir_data

    def set_fhir_data(self, fhir_data: CdsFhirData):
        self._fhir_data = fhir_data

    def get_ccd_data(self) -> Optional[CcdData]:
        return self._ccd_data

    def set_ccd_data(self, ccd_data: CcdData):
        self._ccd_data = ccd_data


@dataclass
class CdsAnnotations:
    """
    Container for Clinical Decision Support (CDS) results.

    This class stores the outputs from clinical decision support systems,
    including CDS Hooks cards and suggested clinical actions. The cards contain
    recommendations, warnings, and other decision support content that can be
    displayed to clinicians. Actions represent specific clinical tasks or
    interventions that are suggested based on the analysis.

    Attributes:
        _cards (Optional[List[Card]]): Internal storage for CDS Hooks cards containing
            clinical recommendations, warnings, or other decision support content.
        _actions (Optional[List[Action]]): Internal storage for suggested clinical actions
            that could be taken based on the CDS analysis.

    Methods:
        set_cards(cards: List[Card]): Sets the list of CDS Hooks cards
        get_cards() -> Optional[List[Card]]: Returns the current list of cards if any exist
        set_actions(actions: List[Action]): Sets the list of suggested clinical actions
        get_actions() -> Optional[List[Action]]: Returns the current list of actions if any exist
    """

    _cards: Optional[List[Card]] = None
    _actions: Optional[List[Action]] = None

    def set_cards(self, cards: List[Card]):
        self._cards = cards

    def get_cards(self) -> Optional[List[Card]]:
        return self._cards

    def set_actions(self, actions: List[Action]):
        self._actions = actions

    def get_actions(self) -> Optional[List[Action]]:
        return self._actions


@dataclass
class Document(BaseDocument):
    """
    A document container that extends BaseDocument with rich annotation capabilities.

    This class extends BaseDocument to handle textual document data and annotations from
    various sources. It serves as the main data structure passed through processing pipelines,
    accumulating annotations and analysis results at each step.

    The Document class provides a comprehensive representation that can include:
    - Raw text and basic tokenization
    - NLP annotations (tokens, entities, embeddings, spaCy docs)
    - Clinical concepts (problems, medications, allergies)
    - Structured clinical documents (CCD, FHIR)
    - Clinical decision support results (cards, actions)
    - ML model outputs (Hugging Face, LangChain)

    Attributes:
        nlp (NlpAnnotations): Container for NLP-related annotations like tokens and entities
        concepts (ConceptLists): Container for extracted medical concepts
        hl7 (StructuredData): Container for structured clinical documents (CCD, FHIR)
        cds (CdsAnnotations): Container for clinical decision support results
        models (ModelOutputs): Container for ML model outputs

    The class provides methods to:
    - Add and access medical concepts
    - Generate structured clinical documents
    - Get basic text statistics
    - Iterate over tokens
    - Access raw text

    Inherits from:
        BaseDocument: Provides base document functionality and raw text storage
    """

    _nlp: NlpAnnotations = field(default_factory=NlpAnnotations)
    _concepts: ConceptLists = field(default_factory=ConceptLists)
    _hl7: HL7Data = field(default_factory=HL7Data)
    _cds: CdsAnnotations = field(default_factory=CdsAnnotations)
    _models: ModelOutputs = field(default_factory=ModelOutputs)

    @property
    def nlp(self) -> NlpAnnotations:
        return self._nlp

    @property
    def concepts(self) -> ConceptLists:
        return self._concepts

    @property
    def hl7(self) -> HL7Data:
        return self._hl7

    @property
    def cds(self) -> CdsAnnotations:
        return self._cds

    @property
    def models(self) -> ModelOutputs:
        return self._models

    def __post_init__(self):
        """Initialize the document with basic tokenization if needed."""
        super().__post_init__()
        self.text = self.data
        if not self._nlp._tokens:
            self._nlp._tokens = self.text.split()  # Basic tokenization if not provided

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
            self._concepts.problems.extend(problems)
        if medications:
            self._concepts.medications.extend(medications)
        if allergies:
            self._concepts.allergies.extend(allergies)

    def add_cds_cards(
        self, cards: Union[List[Card], List[Dict[str, Any]]]
    ) -> List[Card]:
        if not cards:
            raise ValueError("Cards must be provided as a list!")

        try:
            if isinstance(cards[0], dict):
                cards = [Card(**card) for card in cards]
            elif not isinstance(cards[0], Card):
                raise TypeError("Cards must be either Card objects or dictionaries")
        except (IndexError, KeyError) as e:
            raise ValueError("Invalid card format") from e

        return self._cds.set_cards(cards)

    def add_cds_actions(
        self, actions: Union[List[Action], List[Dict[str, Any]]]
    ) -> List[Action]:
        if not actions:
            raise ValueError("Actions must be provided as a list!")

        try:
            if isinstance(actions[0], dict):
                actions = [Action(**action) for action in actions]
            elif not isinstance(actions[0], Action):
                raise TypeError("Actions must be either Action objects or dictionaries")
        except (IndexError, KeyError) as e:
            raise ValueError("Invalid action format") from e

        return self._cds.set_actions(actions)

    def generate_ccd(self, overwrite: bool = False) -> CcdData:
        """
        Generate a CCD (Continuity of Care Document) from the current medical concepts.

        This method creates or updates a CCD in the hl7 container using the
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
        return self._hl7.update_ccd_from_concepts(self._concepts, overwrite)

    def word_count(self) -> int:
        """
        Get the word count from the document's text.
        """
        return len(self._nlp._tokens)

    def __iter__(self) -> Iterator[str]:
        return iter(self._nlp._tokens)

    def __len__(self) -> int:
        return len(self.text)
