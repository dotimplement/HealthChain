# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import logging
from spacy.language import Language
from spacy.tokens import Doc, Span
from typing import Optional, List, Tuple, Dict, Any
from healthchain.pipeline.models.medcatlite.configs import Config
from healthchain.pipeline.models.medcatlite.contextmodel import ContextModel
from healthchain.pipeline.models.medcatlite.utils import (
    LabelStyle,
    CDB,
    Vocab,
    CuiFilter,
)


logger = logging.getLogger(__name__)


@Language.factory("medcatlite_linker")
def create_linker(nlp: Language, name: str, linker_resources: Dict[str, Any]):
    return Linker(nlp, name, linker_resources)


class Linker:
    def __init__(self, nlp: Language, name: str, linker_resources: Dict[str, Any]):
        """
        Initialize the Linker class.

        Args:
            nlp (Language): The spaCy language object.
            name (str): The name of the component.
            cdb (CDB): The concept database.
            vocab (Vocab): The vocabulary.
            config (Dict[str, Any]): The configuration dictionary.
        """
        self.name = name
        self.cdb: CDB = linker_resources["cdb"]
        self.vocab: Vocab = linker_resources["vocab"]
        self.config: Config = linker_resources["config"]
        self.filter: Optional[CuiFilter] = linker_resources["cui_filter"]
        self.context_model = ContextModel(
            self.cdb, self.vocab, self.config, self.filter
        )
        self._setup_extensions()

    def _setup_extensions(self):
        """
        Set up custom extensions for Doc and Span objects.
        """
        custom_extensions = {
            Span: [
                ("cui", -1),
                ("context_similarity", -1),
            ],
        }
        for obj, extensions in custom_extensions.items():
            for ext_name, default_value in extensions:
                if not obj.has_extension(ext_name):
                    obj.set_extension(ext_name, default=default_value)

    def __call__(self, doc: Doc) -> Doc:
        """
        Process the document to identify and link entities.

        Args:
            doc (Doc): The spaCy document object.

        Returns:
            Doc: The processed document with linked entities.
        """
        doc.ents = []
        linked_entities = self._process_entities(doc)
        doc._.ents = linked_entities
        self._post_process(doc)
        return doc

    def _process_entities(self, doc: Doc) -> List[Span]:
        """
        Process entities in the document to identify and link them.

        Args:
            doc (Doc): The spaCy document object.

        Returns:
            List[Span]: The list of linked entities.
        """
        linked_entities = []
        for entity in doc._.ents:
            if entity._.link_candidates:
                cui, context_similarity = self._process_entity(entity, doc)
                if self._is_valid_entity(cui, context_similarity):
                    self._update_entity(entity, cui, context_similarity)
                    linked_entities.append(entity)
        return linked_entities

    def _process_entity(self, entity: Span, doc: Doc) -> Tuple[Optional[str], float]:
        """
        Process a single entity to determine its CUI and context similarity.

        Args:
            entity (Span): The entity to process.
            doc (Doc): The spaCy document object.

        Returns:
            Tuple[Optional[str], float]: The CUI and context similarity.
        """
        name = entity._.detected_name or "unk-unk"
        cuis = entity._.link_candidates

        if not cuis:
            return None, 0

        if self._should_disambiguate(name, cuis):
            return self.context_model.disambiguate(cuis, entity, name, doc)

        cui = cuis[0]
        context_similarity = self._calculate_similarity(cui, entity, doc)
        return cui, context_similarity

    def _should_disambiguate(self, name: str, cuis: List[str]) -> bool:
        """
        Determine if disambiguation is needed for the given name and CUIs.

        Args:
            name (str): The name of the entity.
            cuis (List[str]): The list of CUIs.

        Returns:
            bool: True if disambiguation is needed, False otherwise.
        """
        cnf_l = self.config.linking
        return (
            len(name) < cnf_l.disamb_length_limit
            or (
                len(cuis) == 1
                and self.cdb.name2cuis2status[name][cuis[0]] in {"PD", "N"}
            )
            or len(cuis) > 1
        )

    def _calculate_similarity(self, cui: str, entity: Span, doc: Doc) -> float:
        """
        Calculate the context similarity for the given CUI and entity.

        Args:
            cui (str): The CUI.
            entity (Span): The entity.
            doc (Doc): The spaCy document object.

        Returns:
            float: The context similarity.
        """
        if self.config.linking.always_calculate_similarity:
            return self.context_model.similarity(cui, entity, doc)
        return 1

    def _is_valid_entity(self, cui: Optional[str], context_similarity: float) -> bool:
        """
        Check if the entity is valid based on CUI and context similarity.

        Args:
            cui (Optional[str]): The CUI.
            context_similarity (float): The context similarity.

        Returns:
            bool: True if the entity is valid, False otherwise.
        """
        if self.filter is None:
            logger.warning("No CuiFilter provided, skipping filtering!")
            return cui is not None and self._check_similarity_threshold(
                cui, context_similarity
            )

        return (
            cui is not None
            and self.filter.check(cui)
            and self._check_similarity_threshold(cui, context_similarity)
        )

    def _check_similarity_threshold(self, cui: str, context_similarity: float) -> bool:
        """
        Check if the context similarity meets the threshold for the given CUI.

        Args:
            cui (str): The CUI.
            context_similarity (float): The context similarity.

        Returns:
            bool: True if the context similarity meets the threshold, False otherwise.
        """
        th_type = self.config.linking.similarity_threshold_type
        threshold = self.config.linking.similarity_threshold

        if th_type == "static":
            return context_similarity >= threshold
        if th_type == "dynamic":
            return (
                context_similarity >= self.cdb.cui2average_confidence[cui] * threshold
            )

        logger.warning(f"Unknown similarity threshold type: {th_type}")
        return False

    def _update_entity(self, entity: Span, cui: str, context_similarity: float):
        """
        Update the entity with the given CUI and context similarity.

        Args:
            entity (Span): The entity to update.
            cui (str): The CUI.
            context_similarity (float): The context similarity.
        """
        entity._.cui = cui
        entity._.context_similarity = context_similarity

    def _post_process(self, doc: Doc):
        """
        Perform post-processing on the document.

        Args:
            doc (Doc): The spaCy document object.
        """
        self._create_main_ann(doc)
        self._apply_pretty_labels(doc)
        self._map_entities_to_groups(doc)

    def _create_main_ann(self, doc: Doc, tuis: Optional[List[str]] = None):
        """
        Create the main annotation for the document.

        Args:
            doc (Doc): The spaCy document object.
            tuis (Optional[List[str]]): List of Type Unique Identifiers to filter entities.

        Returns:
            None: Modifies the doc.ents in-place.
        """
        # Sort entities by length (longest first) to prioritize longer matches
        doc._.ents.sort(key=lambda x: len(x.text), reverse=True)

        tokens_covered = set()
        main_annotations = []

        for entity in doc._.ents:
            if tuis is None or entity._.tui in tuis:
                # Check if any token in the entity is already covered
                if not any(token in tokens_covered for token in entity):
                    # Add all tokens of this entity to the covered set
                    tokens_covered.update(entity)
                    main_annotations.append(entity)

        # Update doc.ents with the new main annotations
        doc.ents = list(doc.ents) + main_annotations

    def _apply_pretty_labels(self, doc: Doc):
        """
        Apply pretty labels to the entities in the document.

        Args:
            doc (Doc): The spaCy document object.
        """
        if self.config.general.make_pretty_labels:
            style = LabelStyle[self.config.general.make_pretty_labels]
            self._make_pretty_labels(doc, style)

    def _make_pretty_labels(self, doc: Doc, style: LabelStyle):
        """
        Make pretty labels for the entities in the document.

        Args:
            doc (Doc): The spaCy document object.
            style (LabelStyle): The label style.
        """
        # TODO: Implement pretty label logic here
        pass

    def _map_entities_to_groups(self, doc: Doc):
        """
        Map entities to groups in the document.

        Args:
            doc (Doc): The spaCy document object.
        """
        if self.config.general.map_cui_to_group and self.cdb.addl_info.get("cui2group"):
            for ent in doc.ents:
                ent._.cui = self.cdb.addl_info["cui2group"].get(ent._.cui, ent._.cui)
