"""Component for extracting FHIR problem lists from NLP annotations."""

import logging

from healthchain.pipeline.components.base import BaseComponent
from healthchain.io.containers import Document

logger = logging.getLogger(__name__)


class FHIRProblemListExtractor(BaseComponent[Document]):
    """
    Component that automatically extracts FHIR Condition resources from NLP entities.

    This component processes NLP annotations from multiple sources (spaCy, generic)
    to create structured FHIR problem lists. It looks for entities that have medical codes
    (from entity linking) and converts them into FHIR Condition resources, adding them to
    the document's problem list.

    Attributes:
        patient_ref: Reference to the patient (e.g., "Patient/123")
        coding_system: The coding system for the conditions (default: SNOMED CT)
        code_attribute: Name of the attribute containing medical codes

    Usage:
        >>> # Default - extracts from spaCy ent._.cui
        >>> extractor = ProblemListExtractor(patient_ref="Patient/456")

        >>> # Custom code attribute - uses ent._.snomed_id
        >>> extractor = ProblemListExtractor(
        ...     code_attribute="snomed_id",
        ...     coding_system="http://snomed.info/sct"
        ... )

        >>> # Works with any framework - extracts from generic entities
        >>> extractor = ProblemListExtractor(code_attribute="cui")

        >>> pipeline.add_node(extractor, position="after", reference="entity_linking")
    """

    def __init__(
        self,
        patient_ref: str = "Patient/123",
        coding_system: str = "http://snomed.info/sct",
        code_attribute: str = "cui",
    ):
        """
        Initialize the ProblemListExtractor.

        Args:
            patient_ref: FHIR reference to the patient
            coding_system: Coding system URI for the conditions
            code_attribute: Name of the spaCy extension attribute containing medical codes
        """
        self.patient_ref = patient_ref
        self.coding_system = coding_system
        self.code_attribute = code_attribute

    def __call__(self, doc: Document) -> Document:
        """
        Extract FHIR conditions from the document's NLP annotations.

        Processes entities from spaCy and generic sources that have medical codes
        and creates corresponding FHIR Condition resources. These are automatically
        added to the document's problem list without overwriting existing conditions.

        Args:
            doc: Document with NLP annotations containing medical entities

        Returns:
            Document: Same document with updated problem list
        """
        # Check if we have any entities to process
        spacy_doc = doc.nlp.get_spacy_doc()
        generic_entities = doc.nlp.get_entities()

        if not spacy_doc and not generic_entities:
            logger.debug("No entities found for problem list extraction")
            return doc

        doc.update_problem_list_from_nlp(
            patient_ref=self.patient_ref,
            coding_system=self.coding_system,
            code_attribute=self.code_attribute,
        )

        logger.debug(
            f"Extracted {len(doc.fhir.problem_list)} conditions to problem list"
        )
        return doc
