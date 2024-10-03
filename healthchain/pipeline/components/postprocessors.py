from healthchain.pipeline.components.basecomponent import BaseComponent
from healthchain.io.containers import Document
from typing import TypeVar, Dict


T = TypeVar("T")


class TextPostProcessor(BaseComponent):
    """
    A component for post-processing text documents, specifically for refining entities.

    This class applies post-coordination rules to entities in a Document object,
    replacing entities with their refined versions based on a lookup dictionary.

    Attributes:
        entity_lookup (Dict[str, str]): A dictionary for entity refinement lookups.
    """

    def __init__(self, postcoordination_lookup: Dict[str, str] = None):
        """
        Initialize the TextPostProcessor with an optional postcoordination lookup.

        Args:
            postcoordination_lookup (Dict[str, str], optional): A dictionary for entity refinement lookups.
                If not provided, an empty dictionary will be used.
        """
        self.entity_lookup = postcoordination_lookup or {}

    def __call__(self, doc: Document) -> Document:
        """
        Apply post-processing to the given Document.

        This method refines the entities in the document based on the entity_lookup.
        If an entity exists in the lookup, it is replaced with its refined version.

        Args:
            doc (Document): The document to be post-processed.

        Returns:
            Document: The post-processed document with refined entities.

        Note:
            If the entity_lookup is empty or the document has no 'entities' attribute,
            the document is returned unchanged.
        """
        if not self.entity_lookup or not hasattr(doc, "entities"):
            return doc

        refined_entities = []
        for entity in doc.get_entities():
            entity_text = entity["text"]
            if entity_text in self.entity_lookup:
                entity["text"] = self.entity_lookup[entity_text]
            refined_entities.append(entity)

        doc.entities = refined_entities

        return doc
