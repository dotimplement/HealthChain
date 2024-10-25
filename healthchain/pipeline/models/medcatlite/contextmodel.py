import random
import numpy as np
import logging
from spacy.tokens import Doc, Span, Token
from typing import Dict, List, Optional, Tuple

from healthchain.pipeline.models.medcatlite.configs import Config
from healthchain.pipeline.models.medcatlite.utils import (
    CDB,
    Vocab,
    CuiFilter,
    unitvec,
)


logger = logging.getLogger(__name__)


class ContextModel:
    """
    A model for learning embeddings for concepts and calculating similarities in new documents.
    """

    def __init__(
        self,
        cdb: CDB,
        vocab: Vocab,
        config: Config,
        cui_filter: Optional[CuiFilter] = None,
    ) -> None:
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
        self.filter = cui_filter

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
        for context_type, size in self.config.linking.context_vector_sizes.items():
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
            self.cdb.weighted_average_function(step) * vec
            for step, t in zip(step_range, tokens)
            if (vec := self.vocab.vec(t.lower_)) is not None
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
        if self.config.linking.context_ignore_center_tokens:
            logger.debug("Ignoring center tokens")
            return []

        if (
            cui
            and random.random() > self.config.linking.random_replacement_unsupervised
            and self.cdb.cui2names.get(cui)
        ):
            new_tokens = random.choice(list(self.cdb.cui2names[cui])).split(
                self.config.general.separator
            )
            vectors = [
                vec for t in new_tokens if (vec := self.vocab.vec(t)) is not None
            ]
            logger.debug(f"Using {len(vectors)} CUI-based center token vectors")
        else:
            vectors = [
                vec for t in tokens if (vec := self.vocab.vec(t.lower_)) is not None
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
            or self.cdb.cui2count_train.get(cui, 0)
            < self.config.linking.train_count_threshold
        ):
            logger.debug(f"Insufficient training data for CUI {cui}")
            return -1

        similarity = sum(
            self.config.linking.context_vector_weights[context_type]
            * np.dot(unitvec(vectors[context_type]), unitvec(cui_vectors[context_type]))
            for context_type in self.config.linking.context_vector_weights
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

        if self.config.linking.filter_before_disamb:
            if self.filter is not None:
                cuis = [cui for cui in cuis if self.filter.check(cui)]
            else:
                logger.warning("No CuiFilter provided, skipping filtering!")

            logger.debug(f"Filtered CUIs: {cuis}")

        if not cuis:
            logger.debug("No CUIs left after filtering")
            return None, 0

        similarities = [self._similarity(cui, vectors) for cui in cuis]
        logger.debug(f"Initial similarities: {list(zip(cuis, similarities))}")

        if self.config.linking.prefer_primary_name > 0:
            self._adjust_primary_name_similarities(cuis, similarities, name)

        if self.config.linking.prefer_frequent_concepts > 0:
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
                    similarities[i] * (1 + self.config.linking.prefer_primary_name),
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
            np.log10(count / min_count) * self.config.linking.prefer_frequent_concepts
            if count > 10
            else 0
            for count in counts
        ]

        for i, (cui, old_sim) in enumerate(zip(cuis, similarities)):
            similarities[i] = min(0.99, old_sim * (1 + scales[i]))
            logger.debug(
                f"Adjusted similarity for frequent concept {cui}: {old_sim} -> {similarities[i]}"
            )
