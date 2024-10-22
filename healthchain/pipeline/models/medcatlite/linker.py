# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0

import logging
import random
import numpy as np
from spacy.language import Language
from spacy.tokens import Doc, Span, Token
from typing import Optional, List, Tuple, Dict, Any
from healthchain.pipeline.models.medcatlite.medcatutils import (
    CDB,
    Config,
    Vocab,
    LabelStyle,
    unitvec,
)


logger = logging.getLogger(__name__)


class ContextModel(object):
    """
    A model for learning embeddings for concepts and calculating similarities in new documents.
    """

    def __init__(self, cdb: CDB, vocab: Vocab, config: Config) -> None:
        """
        Initialize the ContextModel.

        Args:
            cdb (CDB): The Context Database.
            vocab (Vocab): The vocabulary.
            config (Config): The configuration to be used.
        """
        self.cdb = cdb
        self.vocab = vocab
        self.config = config
        logger.debug("ContextModel initialized")

    def get_context_tokens(
        self, entity: Span, doc: Doc, size: int
    ) -> Tuple[List[Token], List[Token], List[Token]]:
        """
        Get context tokens for an entity, skipping tokens marked as skip.

        Args:
            entity (Span): The entity to look for.
            doc (Doc): The document to look in.
            size (int): The size of the context window.

        Returns:
            Tuple[List[Token], List[Token], List[Token]]: The tokens on the left, center, and right.
        """
        start, end = entity[0].i, entity[-1].i

        def is_valid_token(t):
            return not (t._.to_skip or t.is_stop or t.is_digit or t.is_punct)

        tokens_left = [
            t for t in doc[max(0, start - size) : start] if is_valid_token(t)
        ][::-1]
        tokens_center = list(entity)
        tokens_right = [t for t in doc[end + 1 : end + 1 + size] if is_valid_token(t)]

        logger.debug(
            f"Context tokens: left={len(tokens_left)}, center={len(tokens_center)}, right={len(tokens_right)}"
        )
        return tokens_left, tokens_center, tokens_right

    def get_context_vectors(
        self, entity: Span, doc: Doc, cui: Optional[str] = None
    ) -> Dict[str, np.ndarray]:
        """
        Get context vectors for a given entity and document.

        Args:
            entity (Span): The entity to look for.
            doc (Doc): The document to look in.
            cui (Optional[str]): The CUI of the entity.

        Returns:
            Dict[str, np.ndarray]: The context vectors.
        """
        vectors = {}
        for context_type, size in self.config.linking["context_vector_sizes"].items():
            tokens_left, tokens_center, tokens_right = self.get_context_tokens(
                entity, doc, size
            )

            values = self._get_token_vectors(tokens_left, reverse=True)
            values.extend(self._get_center_token_vectors(tokens_center, cui))
            values.extend(self._get_token_vectors(tokens_right))

            if values:
                vectors[context_type] = np.average(values, axis=0)

        logger.debug(f"Generated context vectors for {len(vectors)} context types")
        return vectors

    def _get_token_vectors(
        self, tokens: List[Token], reverse: bool = False
    ) -> List[np.ndarray]:
        """
        Get weighted token vectors for a list of tokens.

        Args:
            tokens (List[Token]): The list of tokens.
            reverse (bool): Whether to reverse the order of tokens for weighting.

        Returns:
            List[np.ndarray]: The list of weighted token vectors.
        """
        step_range = (
            range(len(tokens)) if not reverse else range(len(tokens) - 1, -1, -1)
        )
        vectors = [
            self.cdb.weighted_average_function(step) * self.vocab.vec(t.lower_)
            for step, t in zip(step_range, tokens)
            if t.lower_ in self.vocab and self.vocab.vec(t.lower_) is not None
        ]
        logger.debug(f"Generated {len(vectors)} token vectors")
        return vectors

    def _get_center_token_vectors(
        self, tokens: List[Token], cui: Optional[str]
    ) -> List[np.ndarray]:
        """
        Get token vectors for the center tokens, potentially replacing them with CUI-based tokens.

        Args:
            tokens (List[Token]): The center tokens.
            cui (Optional[str]): The CUI of the entity.

        Returns:
            List[np.ndarray]: The list of center token vectors.
        """
        if self.config.linking["context_ignore_center_tokens"]:
            logger.debug("Ignoring center tokens")
            return []

        if (
            cui
            and random.random() > self.config.linking["random_replacement_unsupervised"]
            and self.cdb.cui2names.get(cui)
        ):
            new_tokens = random.choice(list(self.cdb.cui2names[cui])).split(
                self.config.general["separator"]
            )
            vectors = [
                self.vocab.vec(t)
                for t in new_tokens
                if t in self.vocab and self.vocab.vec(t) is not None
            ]
            logger.debug(f"Using {len(vectors)} CUI-based center token vectors")
        else:
            vectors = [
                self.vocab.vec(t.lower_)
                for t in tokens
                if t.lower_ in self.vocab and self.vocab.vec(t.lower_) is not None
            ]
            logger.debug(f"Using {len(vectors)} original center token vectors")

        return vectors

    def similarity(self, cui: str, entity: Span, doc: Doc) -> float:
        """
        Calculate the similarity between the learned context for this CUI and the context in the given document.

        Args:
            cui (str): The CUI.
            entity (Span): The entity to look for.
            doc (Doc): The document to look in.

        Returns:
            float: The similarity score.
        """
        vectors = self.get_context_vectors(entity, doc)
        sim = self._similarity(cui, vectors)
        logger.debug(f"Calculated similarity for CUI {cui}: {sim}")
        return sim

    def _similarity(self, cui: str, vectors: Dict[str, np.ndarray]) -> float:
        """
        Calculate similarity once we have vectors and a CUI.

        Args:
            cui (str): The CUI.
            vectors (Dict[str, np.ndarray]): The context vectors.

        Returns:
            float: The similarity score.
        """
        cui_vectors = self.cdb.cui2context_vectors.get(cui, {})
        if (
            not cui_vectors
            or self.cdb.cui2count_train[cui]
            < self.config.linking["train_count_threshold"]
        ):
            logger.debug(f"Insufficient training data for CUI {cui}")
            return -1

        similarity = sum(
            self.config.linking["context_vector_weights"][context_type]
            * np.dot(unitvec(vectors[context_type]), unitvec(cui_vectors[context_type]))
            for context_type in self.config.linking["context_vector_weights"]
            if context_type in vectors and context_type in cui_vectors
        )

        logger.debug(f"Calculated similarity for CUI {cui}: {similarity}")
        return similarity

    def disambiguate(
        self, cuis: List[str], entity: Span, name: str, doc: Doc
    ) -> Tuple[Optional[str], float]:
        """
        Disambiguate between multiple CUIs for a given entity.

        Args:
            cuis (List[str]): The list of candidate CUIs.
            entity (Span): The entity to disambiguate.
            name (str): The name of the entity.
            doc (Doc): The document containing the entity.

        Returns:
            Tuple[Optional[str], float]: The selected CUI and its similarity score.
        """
        vectors = self.get_context_vectors(entity, doc)
        filters = self.config.linking["filters"]

        if self.config.linking["filter_before_disamb"]:
            cuis = [cui for cui in cuis if filters.check_filters(cui)]
            logger.debug(f"Filtered CUIs: {cuis}")

        if not cuis:
            logger.debug("No CUIs left after filtering")
            return None, 0

        similarities = [self._similarity(cui, vectors) for cui in cuis]
        logger.debug(f"Initial similarities: {list(zip(cuis, similarities))}")

        if self.config.linking.get("prefer_primary_name", 0) > 0:
            self._adjust_primary_name_similarities(cuis, similarities, name)

        if self.config.linking.get("prefer_frequent_concepts", 0) > 0:
            self._adjust_frequent_concept_similarities(cuis, similarities)

        max_index = np.argmax(similarities)
        logger.debug(
            f"Selected CUI: {cuis[max_index]} with similarity {similarities[max_index]}"
        )
        return cuis[max_index], similarities[max_index]

    def _adjust_primary_name_similarities(
        self, cuis: List[str], similarities: List[float], name: str
    ):
        """
        Adjust similarities to prefer primary names.

        Args:
            cuis (List[str]): The list of candidate CUIs.
            similarities (List[float]): The list of similarity scores.
            name (str): The name of the entity.
        """
        for i, cui in enumerate(cuis):
            if similarities[i] > 0 and self.cdb.name2cuis2status.get(name, {}).get(
                cui, ""
            ) in {"P", "PD"}:
                old_sim = similarities[i]
                similarities[i] = min(
                    0.99,
                    similarities[i]
                    * (1 + self.config.linking.get("prefer_primary_name", 0)),
                )
                logger.debug(
                    f"Adjusted similarity for primary name {name}, CUI {cui}: {old_sim} -> {similarities[i]}"
                )

    def _adjust_frequent_concept_similarities(
        self, cuis: List[str], similarities: List[float]
    ):
        """
        Adjust similarities to prefer frequent concepts.

        Args:
            cuis (List[str]): The list of candidate CUIs.
            similarities (List[float]): The list of similarity scores.
        """
        counts = [self.cdb.cui2count_train.get(cui, 0) for cui in cuis]
        min_count = max(min(counts), 1)
        scales = [
            np.log10(count / min_count)
            * self.config.linking.get("prefer_frequent_concepts", 0)
            if count > 10
            else 0
            for count in counts
        ]

        for i, (cui, old_sim) in enumerate(zip(cuis, similarities)):
            similarities[i] = min(0.99, old_sim * (1 + scales[i]))
            logger.debug(
                f"Adjusted similarity for frequent concept {cui}: {old_sim} -> {similarities[i]}"
            )


@Language.factory("medcat_linker")
def create_linker(
    nlp: Language, name: str, cdb: CDB, vocab: Vocab, config: Dict[str, Any]
):
    return Linker(nlp, name, cdb, vocab, config)


class Linker:
    def __init__(
        self, nlp: Language, name: str, cdb: CDB, vocab: Vocab, config: Dict[str, Any]
    ):
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
        self.cdb = cdb
        self.vocab = vocab
        self.config = config
        self.context_model = ContextModel(self.cdb, self.vocab, self.config)
        self._setup_extensions()

    def _setup_extensions(self):
        """
        Set up custom extensions for Doc and Span objects.
        """
        custom_extensions = {
            Doc: [("ents", [])],
            Span: [
                ("detected_name", None),
                ("link_candidates", []),
                ("cui", None),
                ("context_similarity", None),
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
        cnf_l = self.config["linking"]
        return (
            len(name) < cnf_l["disamb_length_limit"]
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
        if self.config["linking"]["always_calculate_similarity"]:
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
        return (
            cui is not None
            and self._check_filters(cui)
            and self._check_similarity_threshold(cui, context_similarity)
        )

    def _check_filters(self, cui: str) -> bool:
        """
        Check if the CUI passes the configured filters.

        Args:
            cui (str): The CUI.

        Returns:
            bool: True if the CUI passes the filters, False otherwise.
        """
        return self.config["linking"]["filters"].check_filters(cui)

    def _check_similarity_threshold(self, cui: str, context_similarity: float) -> bool:
        """
        Check if the context similarity meets the threshold for the given CUI.

        Args:
            cui (str): The CUI.
            context_similarity (float): The context similarity.

        Returns:
            bool: True if the context similarity meets the threshold, False otherwise.
        """
        th_type = self.config["linking"]["similarity_threshold_type"]
        threshold = self.config["linking"]["similarity_threshold"]

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

    def _create_main_ann(self, doc: Doc):
        """
        Create the main annotation for the document.

        Args:
            doc (Doc): The spaCy document object.
        """
        # Implement main annotation creation logic here
        pass

    def _apply_pretty_labels(self, doc: Doc):
        """
        Apply pretty labels to the entities in the document.

        Args:
            doc (Doc): The spaCy document object.
        """
        if self.config["general"]["make_pretty_labels"]:
            style = LabelStyle[self.config["general"]["make_pretty_labels"]]
            self._make_pretty_labels(doc, style)

    def _make_pretty_labels(self, doc: Doc, style: LabelStyle):
        """
        Make pretty labels for the entities in the document.

        Args:
            doc (Doc): The spaCy document object.
            style (LabelStyle): The label style.
        """
        # Implement pretty label logic here
        pass

    def _map_entities_to_groups(self, doc: Doc):
        """
        Map entities to groups in the document.

        Args:
            doc (Doc): The spaCy document object.
        """
        if self.config["general"]["map_cui_to_group"] and self.cdb.addl_info.get(
            "cui2group"
        ):
            self._map_ents_to_groups(doc)

    def _map_ents_to_groups(self, doc: Doc):
        """
        Map entities to groups based on CUI.

        Args:
            doc (Doc): The spaCy document object.
        """
        # Implement entity to group mapping logic here
        pass
