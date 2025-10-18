import logging

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Union
from uuid import uuid4

from spacy.tokens import Doc as SpacyDoc
from spacy.tokens import Span
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.bundle import Bundle
from fhir.resources.documentreference import DocumentReference
from fhir.resources.resource import Resource
from fhir.resources.reference import Reference
from fhir.resources.documentreference import DocumentReferenceRelatesTo
from fhir.resources.operationoutcome import OperationOutcome
from fhir.resources.provenance import Provenance
from fhir.resources.patient import Patient

from healthchain.io.containers.base import BaseDocument
from healthchain.models.responses import Action, Card
from healthchain.fhir import (
    create_bundle,
    add_resource,
    get_resources,
    set_resources,
    extract_resources,
    create_single_codeable_concept,
    read_content_attachment,
    create_condition,
    set_condition_category,
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
class FhirData:
    """
    Container for FHIR resource data and its context.

    Stores and manages clinical data in FHIR format.
    Access document references within resources easily through convenience functions.

    Also allows you to set common continuity of care lists,
    such as a problem list, medication list, and allergy list.
    These collections are accessible as properties of the class instance.

    TODO: make problem, meds, allergy lists configurable

    Properties:
        bundle: The FHIR bundle containing resources
        prefetch_resources: Dictionary of CDS Hooks prefetch resources
        problem_list: List of Condition resources
        medication_list: List of MedicationStatement resources
        allergy_list: List of AllergyIntolerance resources

    Example:
        >>> fhir = FhirData()
        >>> # Add prefetch resources from CDS request
        >>> fhir.prefetch_resources = {"patient": patient_resource}
        >>> # Add document to bundle
        >>> doc_id = fhir.add_document_reference(document)
        >>> # Get document with relationships
        >>> doc_family = fhir.get_document_reference_family(doc_id)
        >>> # Access clinical lists
        >>> conditions = fhir.problem_list
    """

    _prefetch_resources: Optional[Dict[str, Resource]] = None
    _bundle: Optional[Bundle] = None
    _operation_outcomes: List[OperationOutcome] = field(default_factory=list)
    _provenances: List[Provenance] = field(default_factory=list)

    @property
    def bundle(self) -> Optional[Bundle]:
        """Returns the FHIR Bundle if it exists."""
        return self._bundle

    @bundle.setter
    def bundle(self, bundle: Bundle):
        """Sets the FHIR Bundle.
        The bundle is a collection of FHIR resources.
        See: https://www.hl7.org/fhir/bundle.html
        """
        self._bundle = bundle

    @property
    def prefetch_resources(self) -> Optional[Dict[str, Resource]]:
        """Returns the prefetch FHIR resources."""
        return self._prefetch_resources

    @prefetch_resources.setter
    def prefetch_resources(self, resources: Dict[str, Resource]):
        """Sets the prefetch FHIR resources from CDS service requests."""
        self._prefetch_resources = resources

    @property
    def operation_outcomes(self) -> List[OperationOutcome]:
        """Get extracted OperationOutcome resources separated from the bundle."""
        return self._operation_outcomes

    @operation_outcomes.setter
    def operation_outcomes(self, outcomes: List[OperationOutcome]) -> None:
        self._operation_outcomes = outcomes or []

    @property
    def provenances(self) -> List[Provenance]:
        """Get extracted Provenance resources separated from the bundle."""
        return self._provenances

    @provenances.setter
    def provenances(self, provenances: List[Provenance]) -> None:
        self._provenances = provenances or []

    @property
    def patient(self) -> Optional[Patient]:
        """Get the first Patient resource from the bundle (convenience accessor).

        Returns None if no Patient resources are present in the bundle.
        For bundles with multiple patients, use the patients property instead.
        """
        patients = self.get_resources("Patient")
        return patients[0] if patients else None

    @property
    def patients(self) -> List[Patient]:
        """Get all Patient resources from the bundle.

        Most bundles contain a single patient, but some queries (e.g., family history,
        population queries) may return multiple patients. This property provides access
        to all Patient resources without removing them from the bundle.
        """
        return self.get_resources("Patient")

    @property
    def problem_list(self) -> List[Condition]:
        """Get problem list from the bundle.
        Problem list items are stored as Condition resources in the bundle.
        See: https://www.hl7.org/fhir/condition.html
        """
        return self.get_resources("Condition")

    @problem_list.setter
    def problem_list(self, value: Union[List[Condition], Dict[str, Any]]) -> None:
        """
        Set problem list in the bundle.

        By default, this adds the provided conditions to any existing conditions in the bundle.
        To replace existing conditions instead, pass a dictionary with 'resources' and 'replace' keys.

        Args:
            value: Either a list of Condition resources (adds by default) or a dict with:
                - 'resources': List of Condition resources
                - 'replace': bool, whether to replace existing resources (default: False)

        Examples:
            >>> # Add to existing conditions (default behavior)
            >>> fhir.problem_list = [condition1, condition2]
            >>> # Replace existing conditions
            >>> fhir.problem_list = {'resources': [condition1], 'replace': True}
        """
        if isinstance(value, dict):
            resources = value.get("resources", [])
            replace = value.get("replace", False)
        else:
            resources = value
            replace = False

        self.add_resources(resources, "Condition", replace=replace)

    @property
    def medication_list(self) -> List[MedicationStatement]:
        """Get medication list from the bundle."""
        return self.get_resources("MedicationStatement")

    @medication_list.setter
    def medication_list(
        self, value: Union[List[MedicationStatement], Dict[str, Any]]
    ) -> None:
        """
        Set medication list in the bundle.

        By default, this adds the provided medications to any existing medications in the bundle.
        To replace existing medications instead, pass a dictionary with 'resources' and 'replace' keys.

        Args:
            value: Either a list of MedicationStatement resources (adds by default) or a dict with:
                - 'resources': List of MedicationStatement resources
                - 'replace': bool, whether to replace existing resources (default: False)

        Examples:
            >>> # Add to existing medications (default behavior)
            >>> fhir.medication_list = [medication1, medication2]
            >>> # Replace existing medications
            >>> fhir.medication_list = {'resources': [medication1], 'replace': True}
        """
        if isinstance(value, dict):
            resources = value.get("resources", [])
            replace = value.get("replace", False)
        else:
            resources = value
            replace = False

        self.add_resources(resources, "MedicationStatement", replace=replace)

    @property
    def allergy_list(self) -> List[AllergyIntolerance]:
        """Get allergy list from the bundle."""
        return self.get_resources("AllergyIntolerance")

    @allergy_list.setter
    def allergy_list(
        self, value: Union[List[AllergyIntolerance], Dict[str, Any]]
    ) -> None:
        """
        Set allergy list in the bundle.

        By default, this adds the provided allergies to any existing allergies in the bundle.
        To replace existing allergies instead, pass a dictionary with 'resources' and 'replace' keys.

        Args:
            value: Either a list of AllergyIntolerance resources (adds by default) or a dict with:
                - 'resources': List of AllergyIntolerance resources
                - 'replace': bool, whether to replace existing resources (default: False)

        Examples:
            >>> # Add to existing allergies (default behavior)
            >>> fhir.allergy_list = [allergy1, allergy2]
            >>> # Replace existing allergies
            >>> fhir.allergy_list = {'resources': [allergy1], 'replace': True}
        """
        if isinstance(value, dict):
            resources = value.get("resources", [])
            replace = value.get("replace", False)
        else:
            resources = value
            replace = False

        self.add_resources(resources, "AllergyIntolerance", replace=replace)

    def get_prefetch_resources(self, key: str) -> List[Any]:
        """Get resources of a specific type from the prefetch bundle."""
        if not self._prefetch_resources:
            return []
        return self._prefetch_resources.get(key, [])

    def get_resources(self, resource_type: str) -> List[Any]:
        """Get resources of a specific type from the working bundle."""
        if not self._bundle:
            return []
        return get_resources(self._bundle, resource_type)

    def add_resources(
        self, resources: List[Any], resource_type: str, replace: bool = False
    ):
        """Add resources to the working bundle."""
        if not self._bundle:
            self._bundle = create_bundle()
        set_resources(self._bundle, resources, resource_type, replace=replace)

    def add_document_reference(
        self,
        document: DocumentReference,
        parent_id: Optional[str] = None,
        relationship_type: Optional[str] = "transforms",
    ) -> str:
        """
        Adds a DocumentReference resource to the FHIR bundle and establishes
        relationships between documents if a parent_id is provided. The relationship is
        tracked using the FHIR relatesTo element with a specified relationship type.
        See: https://build.fhir.org/documentreference-definitions.html#DocumentReference.relatesTo

        Args:
            document: The DocumentReference to add to the bundle
            parent_id: Optional ID of the parent document. If provided, establishes a
                relationship between this document and its parent.
            relationship_type: The type of relationship to establish with the parent
                document. Defaults to "transforms". This is used in the FHIR relatesTo
                element's code. See: http://hl7.org/fhir/valueset-document-relationship-type

        Returns:
            str: The ID of the added document. If the document had no ID, a new UUID-based
                ID is generated.
        """
        # Generate a consistent ID if not present
        if not document.id:
            document.id = f"doc-{uuid4()}"

        # Add relationship metadata if there's a parent
        if parent_id:
            if not hasattr(document, "relatesTo") or not document.relatesTo:
                document.relatesTo = []
            document.relatesTo.append(
                DocumentReferenceRelatesTo(
                    target=Reference(reference=f"DocumentReference/{parent_id}"),
                    code=create_single_codeable_concept(
                        code=relationship_type,
                        display=relationship_type.capitalize(),
                        system="http://hl7.org/fhir/ValueSet/document-relationship-type",
                    ),
                )
            )

        self.add_resources([document], "DocumentReference", replace=False)

        return document.id

    def get_document_references_readable(
        self, include_data: bool = True, include_relationships: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get DocumentReferences resources with their content and optional relationship data
        in a human-readable dictionary format.

        Args:
            include_data: If True, decode and include the document data (default: True)
            include_relationships: If True, include related document information (default: True)

        Returns:
            List of documents with metadata and optionally their content and relationships
        """
        documents = []
        for doc in self.get_resources("DocumentReference"):
            doc_data = {
                "id": doc.id,
                "description": doc.description,
                "status": doc.status,
            }

            attachments = read_content_attachment(doc, include_data=include_data)
            if attachments:
                doc_data["attachments"] = []
                for attachment in attachments:
                    if include_data:
                        doc_data["attachments"].append(
                            {
                                "data": attachment.get("data"),
                                "metadata": attachment.get("metadata"),
                            }
                        )
                    else:
                        doc_data["attachments"].append(
                            {"metadata": attachment.get("metadata")}
                        )

            if include_relationships:
                family = self.get_document_reference_family(doc.id)
                doc_data["relationships"] = {
                    "parents": [
                        {"id": p.id, "description": p.description}
                        for p in family["parents"]
                    ],
                    "children": [
                        {"id": c.id, "description": c.description}
                        for c in family["children"]
                    ],
                    "siblings": [
                        {"id": s.id, "description": s.description}
                        for s in family["siblings"]
                    ],
                }

            documents.append(doc_data)

        return documents

    def get_document_reference_family(self, document_id: str) -> Dict[str, Any]:
        """
        Get a DocumentReference resource and all its related resources
        based on the relatesTo element in the FHIR standard.
        See: https://build.fhir.org/documentreference-definitions.html#DocumentReference.relatesTo

        Args:
            document_id: ID of the DocumentReference resource to find relationships for

        Returns:
            Dict containing:
                'document': The requested DocumentReference resource
                'parents': List of parent DocumentReference resources
                'children': List of child DocumentReference resources
                'siblings': List of DocumentReference resources sharing the same parent
        """
        documents = self.get_resources("DocumentReference")
        family = {"document": None, "parents": [], "children": [], "siblings": []}

        # Find the requested document
        target_doc = next((doc for doc in documents if doc.id == document_id), None)
        if not target_doc:
            return family

        family["document"] = target_doc

        # Find direct relationships
        if hasattr(target_doc, "relatesTo") and target_doc.relatesTo:
            # Find parents from target's relationships
            for relation in target_doc.relatesTo:
                parent_ref = relation.target.reference
                parent_id = parent_ref.split("/")[-1]
                parent = next((doc for doc in documents if doc.id == parent_id), None)
                if parent:
                    family["parents"].append(parent)

        # Find children and siblings
        for doc in documents:
            if not hasattr(doc, "relatesTo") or not doc.relatesTo:
                continue

            for relation in doc.relatesTo:
                target_ref = relation.target.reference
                related_id = target_ref.split("/")[-1]

                # Check if this doc is a child of our target
                if related_id == document_id:
                    family["children"].append(doc)

                # For siblings, check if they share the same parent
                elif family["parents"] and related_id == family["parents"][0].id:
                    if doc.id != document_id:  # Don't include self as sibling
                        family["siblings"].append(doc)

        return family


@dataclass
class CdsAnnotations:
    """
    Container for Clinical Decision Support (CDS) results.

    This class stores and manages outputs from clinical decision support systems,
    including CDS Hooks cards and suggested clinical actions. The cards contain
    recommendations, warnings, and other decision support content that can be
    displayed to clinicians. Actions represent specific clinical tasks or
    interventions that are suggested based on the analysis.

    Attributes:
        _cards (Optional[List[Card]]): CDS Hooks cards containing clinical
            recommendations, warnings, or other decision support content.
        _actions (Optional[List[Action]]): Suggested clinical actions that
            could be taken based on the CDS analysis.

    Example:
        >>> cds = CdsAnnotations()
        >>> cds.cards = [Card(summary="Consider aspirin")]
        >>> cds.actions = [Action(type="create", description="Order aspirin")]
    """

    _cards: Optional[List[Card]] = None
    _actions: Optional[List[Action]] = None

    @property
    def cards(self) -> Optional[List[Card]]:
        """Get the current list of CDS Hooks cards."""
        return self._cards

    @cards.setter
    def cards(self, cards: Union[List[Card], List[Dict[str, Any]]]) -> None:
        """
        Set CDS Hooks cards, converting from dictionaries if needed.

        Args:
            cards: List of Card objects or dictionaries that can be converted to Cards.

        Raises:
            ValueError: If cards list is empty or has invalid format.
            TypeError: If cards are neither Card objects nor dictionaries.
        """
        if not cards:
            raise ValueError("Cards must be provided as a list!")

        try:
            if isinstance(cards[0], dict):
                self._cards = [Card(**card) for card in cards]
            elif isinstance(cards[0], Card):
                self._cards = cards
            else:
                raise TypeError("Cards must be either Card objects or dictionaries")
        except (IndexError, KeyError) as e:
            raise ValueError("Invalid card format") from e

    @property
    def actions(self) -> Optional[List[Action]]:
        """Get the current list of suggested clinical actions."""
        return self._actions

    @actions.setter
    def actions(self, actions: Union[List[Action], List[Dict[str, Any]]]) -> None:
        """
        Set suggested clinical actions, converting from dictionaries if needed.

        Args:
            actions: List of Action objects or dictionaries that can be converted to Actions.

        Raises:
            ValueError: If actions list is empty or has invalid format.
            TypeError: If actions are neither Action objects nor dictionaries.
        """
        if not actions:
            raise ValueError("Actions must be provided as a list!")

        try:
            if isinstance(actions[0], dict):
                self._actions = [Action(**action) for action in actions]
            elif isinstance(actions[0], Action):
                self._actions = actions
            else:
                raise TypeError("Actions must be either Action objects or dictionaries")
        except (IndexError, KeyError) as e:
            raise ValueError("Invalid action format") from e


@dataclass
class Document(BaseDocument):
    """
    Main document container for processing textual and clinical data in HealthChain.

    The Document class is the primary structure used throughout annotation and analytics
    pipelines, accumulating transformations, extractions, and results from each stage. It
    seamlessly integrates raw text, NLP annotations, FHIR resources, clinical decision
    support (CDS) results, and ML model outputs in one object.

    Features:
        - Accepts text, FHIR Bundles/resources, or lists of FHIR resources as input.
        - Provides basic tokenization and supports integration with NLP models (spaCy, transformers).
        - Stores and manipulates clinical FHIR data via the .fhir property (access to bundles, problem lists, meds, allergies, etc.).
        - Encapsulates CDS Hooks-style decision support cards and suggested actions via the .cds property.
        - Stores outputs from external ML/LLM models: HuggingFace, LangChain, etc.

    Attributes:
        nlp (NlpAnnotations): NLP output (tokens, entities, embeddings, spaCy doc)
        fhir (FhirData): FHIR resources and context (problem list, medication, allergy, etc.)
        cds (CdsAnnotations): Clinical decision support (cards and actions)
        models (ModelOutputs): Results from ML/LLM models (HuggingFace, LangChain, etc.)
        text (str): The text content of the document (if available).
        data: The original input supplied (raw text, Bundle, resource, or list of resources)

    Usage example:
        >>> doc = Document(data="Patient has hypertension")
        >>> doc.nlp._tokens
        ['Patient', 'has', 'hypertension']
        >>> doc.fhir.problem_list = [Condition(...)]
        >>> doc.cds.cards = [Card(...)]
        >>> doc.models.huggingface_results = ...
        >>> for token in doc:
        ...     print(token)

    Inherits from:
        BaseDocument
    """

    _nlp: NlpAnnotations = field(default_factory=NlpAnnotations)
    _fhir: FhirData = field(default_factory=FhirData)
    _cds: CdsAnnotations = field(default_factory=CdsAnnotations)
    _models: ModelOutputs = field(default_factory=ModelOutputs)

    @property
    def nlp(self) -> NlpAnnotations:
        return self._nlp

    @property
    def fhir(self) -> FhirData:
        return self._fhir

    @property
    def cds(self) -> CdsAnnotations:
        return self._cds

    @property
    def models(self) -> ModelOutputs:
        return self._models

    def __post_init__(self):
        """
        Post-initialization setup to process textual or FHIR data.

        - If input data is a FHIR Bundle, stores it and extracts OperationOutcome and Provenance resources.
        - If input data is a list of FHIR resources, wraps them in a Bundle.
        - For text input, sets .text field accordingly.
        - Performs basic whitespace tokenization if necessary.
        """
        super().__post_init__()

        # Handle FHIR Bundle data
        if isinstance(self.data, Bundle):
            self._fhir._bundle = self.data

            # Extract OperationOutcome resources (operation results/errors)
            outcomes = extract_resources(self._fhir._bundle, "OperationOutcome")
            if outcomes:
                self._fhir._operation_outcomes = outcomes

            # Extract Provenance resources (data lineage/origin)
            provenances = extract_resources(self._fhir._bundle, "Provenance")
            if provenances:
                self._fhir._provenances = provenances

            self.text = ""  # No text content for bundle-only documents
        # Handle list of FHIR resources
        elif (
            isinstance(self.data, list)
            and self.data
            and isinstance(self.data[0], Resource)
        ):
            self._fhir._bundle = create_bundle()
            for resource in self.data:
                add_resource(self._fhir._bundle, resource)
            self.text = ""  # No text content for resource-only documents
        else:
            # Handle text data
            self.text = self.data if isinstance(self.data, str) else str(self.data)

        if not self._nlp._tokens and self.text:
            self._nlp._tokens = self.text.split()  # Basic tokenization if not provided

    def word_count(self) -> int:
        """
        Return the number of word tokens in the document.

        Returns:
            int: The count of tokenized words in the document.
        """
        return len(self._nlp._tokens)

    def update_problem_list_from_nlp(
        self,
        patient_ref: str = "Patient/123",
        coding_system: str = "http://snomed.info/sct",
        code_attribute: str = "cui",
    ):
        """
        Populate or update the problem list using entities extracted via NLP.

        This method looks for entities with associated medical codes and creates FHIR Condition
        resources from them. It supports a two-step process:
        1. NER: Extract entities from text (spaCy, HuggingFace, etc.)
        2. Entity Linking: Add medical codes to those entities
        3. Problem List Creation: Convert linked entities to FHIR conditions (this method)

        The method extracts from:
        1. spaCy entities with extension attributes (e.g., ent._.cui)
        2. Generic entities in the NLP annotations container (framework-agnostic)

        TODO: make this more generic and support other resource types

        Args:
            patient_ref: FHIR reference to the patient (default: "Patient/123")
            coding_system: Coding system URI for the conditions (default: SNOMED CT)
            code_attribute: Name of the attribute containing the medical code (default: "cui")

        Notes:
            - Preserves any existing problem list Conditions.
            - Supports framework-agnostic extraction (spaCy and dict entities).
            - For spaCy, looks for entity extension attribute (e.g. ent._.cui).
            - For non-spaCy, expects codes as dict keys (ent["cui"], etc.).
        """
        # Start with existing conditions to preserve them
        existing_conditions = self.fhir.problem_list.copy()
        new_conditions = []

        # 1. Extract from spaCy entities (if available)
        if self.nlp._spacy_doc and self.nlp._spacy_doc.ents:
            for ent in self.nlp._spacy_doc.ents:
                if not Span.has_extension(code_attribute):
                    logger.debug(
                        f"Extension '{code_attribute}' not found for spaCy entity {ent.text}"
                    )
                    continue

                code_value = getattr(ent._, code_attribute, None)
                if code_value is None:
                    logger.debug(
                        f"No {code_attribute} found for spaCy entity {ent.text}"
                    )
                    continue

                condition = create_condition(
                    subject=patient_ref,
                    code=code_value,
                    display=ent.text,
                    system=coding_system,
                )
                set_condition_category(condition, "problem-list-item")
                logger.debug(
                    f"Adding condition from spaCy: {condition.model_dump(exclude_none=True)}"
                )
                new_conditions.append(condition)

        # 2. Extract from generic NLP entities (framework-agnostic)
        generic_entities = self.nlp.get_entities()
        if generic_entities:
            for ent_dict in generic_entities:
                # Skip if no linked code
                code_value = ent_dict.get(code_attribute)
                if code_value is None:
                    logger.debug(
                        f"No {code_attribute} found for entity {ent_dict.get('text', 'unknown')}"
                    )
                    continue

                entity_text = ent_dict.get("text", "unknown")

                condition = create_condition(
                    subject=patient_ref,
                    code=code_value,
                    display=entity_text,
                    system=coding_system,
                )
                set_condition_category(condition, "problem-list-item")
                logger.debug(
                    f"Adding condition from entities: {condition.model_dump(exclude_none=True)}"
                )
                new_conditions.append(condition)

        # Update problem list with combined conditions (replace to avoid duplication)
        if new_conditions:
            all_conditions = existing_conditions + new_conditions
            self.fhir.add_resources(all_conditions, "Condition", replace=True)

    def __iter__(self) -> Iterator[str]:
        """
        Iterate through the document's tokens.

        Returns:
            Iterator[str]: Iterator over the document tokens.
        """
        return iter(self._nlp._tokens)

    def __len__(self) -> int:
        """
        Return the length of the document's text.

        Returns:
            int: Character length of the document text.
        """
        return len(self.text)
