from dataclasses import dataclass
from healthchain.pipeline.components.basecomponent import Component
from healthchain.io.containers import Document
from typing import TypeVar, Dict


T = TypeVar("T")


@dataclass
class TextPostProcessorConfig:
    """
    Configuration for the TextPostProcessor.

    Attributes:
        postcoordination_lookup (Dict[str, str], optional): A dictionary for entity refinement lookups.
            Defaults to None.
    """

    postcoordination_lookup: Dict[str, str] = None


class TextPostProcessor(Component[T]):
    """
    A component for post-processing text documents, specifically for refining entities.

    This class applies post-coordination rules to entities in a Document object,
    replacing entities with their refined versions based on a lookup dictionary.

    Attributes:
        config (TextPostProcessorConfig): Configuration for the post-processor.
        entity_lookup (Dict[str, str]): A dictionary for entity refinement lookups.

    """

    def __init__(self, config: TextPostProcessorConfig = None):
        """
        Initialize the TextPostProcessor with an optional configuration.

        Args:
            config (TextPostProcessorConfig, optional): Configuration for the post-processor.
                If not provided, a default configuration will be used.
        """
        self.config = config or TextPostProcessorConfig()
        self.entity_lookup = self.config.postcoordination_lookup or {}

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
            print(doc.entities)
            print(entity)
            print(self.entity_lookup)
            entity_text = entity["text"]
            if entity_text in self.entity_lookup:
                entity["text"] = self.entity_lookup[entity_text]
            refined_entities.append(entity)

        doc.entities = refined_entities

        return doc
