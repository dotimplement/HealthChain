# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import logging
import os
import random
import json
import shutil
import pickle
import numpy as np
from spacy.tokens import Doc, Span
from typing import (
    Callable,
    Dict,
    Iterable,
    Protocol,
    Set,
    Optional,
    List,
    Tuple,
    Type,
    Union,
    Any,
)
from enum import Enum
from functools import partial
from gensim.matutils import unitvec as g_unitvec
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


def unitvec(arr):
    return g_unitvec(np.array(arr))


class LabelStyle(Enum):
    LONG = 1
    SHORT = 2


def attempt_unpack(zip_path: str) -> str:
    """Attempt unpack the zip to a folder and get the model pack path.

    If the folder already exists, no unpacking is done.

    Args:
        zip_path (str): The ZIP path

    Returns:
        str: The model pack path
    """
    base_dir = os.path.dirname(zip_path)
    filename = os.path.basename(zip_path)
    foldername = filename.replace(".zip", "")
    model_pack_path = os.path.join(base_dir, foldername)
    if os.path.exists(model_pack_path):
        logger.info(
            "Found an existing unzipped model pack at: {}, the provided zip will not be touched.".format(
                model_pack_path
            )
        )
    else:
        logger.info("Unziping the model pack and loading models.")
        shutil.unpack_archive(zip_path, extract_dir=model_pack_path)
    return model_pack_path


class CustomUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.startswith("medcat"):
            return getattr(CDB, name, type(name, (), {}))
        return super().find_class(module, name)


def deserialize_cdb(file_path: str, cdb_cls: Type[Any]):
    """
    Deserializes a CDB object from a file.

    Args:
        file_path (str): The path to the serialized CDB file.
        cdb_cls (Type[Any]): The CDB class to instantiate.

    Returns:
        Any: An instance of cdb_cls with the deserialized data.

    Raises:
        ValueError: If the data format in the file is unexpected.
        IOError: If there's an issue reading the file.
    """
    try:
        with open(file_path, "rb") as f:
            data = CustomUnpickler(f).load()
    except IOError as e:
        raise IOError(f"Error reading file {file_path}: {str(e)}")
    cdb = cdb_cls()
    if "cdb" in data:
        cdb.__dict__.update(data["cdb"])
    elif "cdb_main" in data:
        cdb.__dict__.update(data["cdb_main"])
    else:
        raise ValueError("Unexpected data format in serialized file")
    return cdb


class WAFCarrier(Protocol):
    @property
    def weighted_average_function(self) -> Callable[[float], int]:
        return


def weighted_average(step: int, factor: float) -> float:
    return max(0.1, 1 - step**2 * factor)


def fix_waf_lambda(carrier: WAFCarrier) -> None:
    weighted_average_function = carrier.weighted_average_function
    if callable(weighted_average_function):
        if getattr(weighted_average_function, "__name__", None) == "<lambda>":
            carrier.weighted_average_function = partial(weighted_average, factor=0.0004)


class GeneralConfig(BaseModel):
    spacy_model: str = "en_core_web_md"
    spacy_disabled_components: List[str] = [
        "ner",
        "parser",
        "vectors",
        "textcat",
        "entity_linker",
        "sentencizer",
        "entity_ruler",
        "merge_noun_chunks",
        "merge_entities",
        "merge_subtokens",
    ]
    spell_check: bool = True
    workers: int = 4


class NERConfig(BaseModel):
    min_name_len: int = 3
    max_skip_tokens: int = 2


class LinkingConfig(BaseModel):
    train_count_threshold: int = 1
    similarity_threshold: float = 0.25
    context_vector_sizes: Dict[str, int] = Field(
        default_factory=lambda: {"long": 18, "medium": 9, "short": 3}
    )
    context_vector_weights: Dict[str, float] = Field(
        default_factory=lambda: {"long": 0.5, "medium": 0.3, "short": 0.2}
    )


class PreprocessingConfig(BaseModel):
    punct_checker: str = "[^\\w\\s]"
    word_skipper: str = "^$"
    keep_punct: List[str] = Field(default_factory=list)
    skip_stopwords: bool = True
    min_len_normalize: int = 2
    do_not_normalize: List[str] = Field(default_factory=list)


class Config(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    ner: NERConfig = Field(default_factory=NERConfig)
    linking: LinkingConfig = Field(default_factory=LinkingConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.dict(), f, indent=2)

    def merge_config(self, config_dict: Dict[str, Any]) -> None:
        for section, values in config_dict.items():
            if hasattr(self, section):
                current_section = getattr(self, section)
                current_section_dict = current_section.dict()
                current_section_dict.update(values)
                setattr(self, section, type(current_section)(**current_section_dict))


class CDB:
    def __init__(self, config: Union[Config, None] = None):
        if config is None:
            self.config = Config()
            self._config_from_file = False
        else:
            self.config = config
            self._config_from_file = True
        self.name2cuis2status = {}
        self.cui2average_confidence = {}
        self.addl_info = {}
        self.snames = set()
        self.cui2snames = {}
        self.cui2names = {}
        self.cui2context_vectors = {}
        self.cui2count_train = {}
        self.name2count_train = {}
        self.weighted_average_function = None

    def __repr__(self):
        return (
            f"CDB(\n"
            f"    config:                 {self.config}\n"
            f"    name2cuis2status:       {self._preview_dict(self.name2cuis2status)}\n"
            f"    cui2average_confidence: {self._preview_dict(self.cui2average_confidence)}\n"
            f"    addl_info:              {self._preview_dict(self.addl_info, value_preview='...')}\n"
            f"    snames:                 {self._preview_set(self.snames)}\n"
            f"    cui2snames:             {self._preview_dict(self.cui2snames, n=1)}\n"
            f"    cui2context_vectors:    {self._preview_dict(self.cui2count_train)}\n"
            f"    name2count_train:       {self._preview_dict(self.name2count_train)}\n"
            f"    weighted_average_function: {self.weighted_average_function}\n"
            f")"
        )

    def _preview_dict(self, d, n=3, value_preview=None):
        preview = dict(list(d.items())[:n])
        if value_preview:
            preview = {k: value_preview for k in preview}
        return f"{preview}, (total: {len(d)})"

    def _preview_set(self, s, n=3):
        return f"{set(list(s)[:n])}, (total: {len(s)})"

    @classmethod
    def load(cls, path: str) -> "CDB":
        cdb = deserialize_cdb(path, cls)
        fix_waf_lambda(cdb)
        return cdb

    def get_snames(self) -> Set[str]:
        if not self.snames and self.cui2snames:
            for snames in self.cui2snames.values():
                self.snames.update(snames)
        return self.snames


class Vocab:
    def __init__(self):
        self.vocab = {}
        self.index2word = {}
        self.vec_index2word = {}
        self.unigram_table = np.array([])

    def __repr__(self):
        return (
            f"Vocab(\n"
            f"    vocab:          {self._preview_dict(self.vocab, value_preview='...')}\n"
            f"    index2word:     {self._preview_dict(self.index2word)}\n"
            f"    vec_index2word: {self._preview_dict(self.vec_index2word)}\n"
            f"    unigram_table:  shape: {self.unigram_table.shape}\n"
            f")"
        )

    def _preview_dict(self, d, n=3, value_preview=None):
        items = list(d.items())[:n]
        if value_preview:
            items = [(k, value_preview) for k, _ in items]
        preview = dict(items)
        return f"{preview}, (total: {len(d)})"

    def vec(self, word: str) -> Optional[np.ndarray]:
        return self.vocab.get(word, {}).get("vec")

    def get_negative_samples(
        self, n: int = 6, ignore_punct_and_num: bool = False
    ) -> List[int]:
        if len(self.unigram_table) == 0:
            raise Exception(
                "No unigram table present, please run the function vocab.make_unigram_table() first."
            )
        inds = np.random.randint(0, len(self.unigram_table), n)
        inds = self.unigram_table[inds]
        if ignore_punct_and_num:
            inds = [ind for ind in inds if self.index2word[ind].upper().isupper()]
        return inds

    def make_unigram_table(self, table_size: int = 100000000) -> None:
        freqs = []
        unigram_table = []
        words = list(self.vec_index2word.values())
        for word in words:
            freqs.append(self.vocab[word]["cnt"])
        freqs = np.array(freqs)
        freqs = np.power(freqs, 0.75)
        sm = np.sum(freqs)
        for ind in self.vec_index2word.keys():
            word = self.vec_index2word[ind]
            f_ind = words.index(word)
            p = freqs[f_ind] / sm
            unigram_table.extend([ind] * int(p * table_size))
        self.unigram_table = np.array(unigram_table)

    def __contains__(self, word: str) -> bool:
        return word in self.vocab

    @classmethod
    def load(cls, path: str) -> "Vocab":
        with open(path, "rb") as f:
            vocab = cls()
            vocab.__dict__ = pickle.load(f)
        return vocab

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self.__dict__, f)


class BasicSpellChecker(object):
    def __init__(self, cdb_vocab, config, data_vocab=None):
        self.vocab = cdb_vocab
        self.config = config
        self.data_vocab = data_vocab

    def P(self, word: str) -> float:
        """Probability of `word`.

        Args:
            word (str): The word in question.

        Returns:
            float: The probability.
        """
        cnt = self.vocab.get(word, 0)
        if cnt != 0:
            return -1 / cnt
        return 0

    def __contains__(self, word):
        if word in self.vocab:
            return True
        if self.data_vocab is not None and word in self.data_vocab:
            return False
        return False

    def fix(self, word: str) -> Optional[str]:
        """Most probable spelling correction for word.

        Args:
            word (str): The word.

        Returns:
            Optional[str]: Fixed word, or None if no fixes were applied.
        """
        fix = max(self.candidates(word), key=self.P)
        if fix != word:
            return fix
        return None

    def candidates(self, word: str) -> Iterable[str]:
        """Generate possible spelling corrections for word.

        Args:
            word (str): The word.

        Returns:
            Iterable[str]: The list of candidate words.
        """
        if self.config.general.spell_check_deep:
            return (
                self.known([word])
                or self.known(self.edits1(word))
                or self.known(self.edits2(word))
                or [word]
            )
        return self.known([word]) or self.known(self.edits1(word)) or [word]

    def known(self, words: Iterable[str]) -> Set[str]:
        """The subset of `words` that appear in the dictionary of WORDS.

        Args:
            words (Iterable[str]): The words.

        Returns:
            Set[str]: The set of candidates.
        """
        return set((w for w in words if w in self.vocab))

    def edits1(self, word: str) -> Set[str]:
        return self.get_edits1(word, self.config.general.diacritics)


class ContextModel(object):
    """Used to learn embeddings for concepts and calculate similarities in new documents.

    Args:
        cdb (CDB): The Context Database
        vocab (Vocab): The vocabulary
        config (Config): The config to be used
    """

    def __init__(self, cdb: CDB, vocab: Vocab, config: Config) -> None:
        self.cdb = cdb
        self.vocab = vocab
        self.config = config

    def get_context_tokens(self, entity: Span, doc: Doc, size: int) -> Tuple:
        """Get context tokens for an entity, this will skip anything that
        is marked as skip in token._.to_skip

        Args:
            entity (Span): The entity to look for.
            doc (Doc): The document look in.
            size (int): The size of the entity.

        Returns:
            Tuple: The tokens on the left, centre, and right.
        """
        start_ind = entity[0].i
        end_ind = entity[-1].i
        tokens_left = [
            tkn
            for tkn in doc[max(0, start_ind - size) : start_ind]
            if not (tkn._.to_skip or tkn.is_stop or tkn.is_digit or tkn.is_punct)
        ]
        tokens_left.reverse()
        tokens_center = list(entity)
        tokens_right = [
            tkn
            for tkn in doc[end_ind + 1 : end_ind + 1 + size]
            if not (tkn._.to_skip or tkn.is_stop or tkn.is_digit or tkn.is_punct)
        ]
        return (tokens_left, tokens_center, tokens_right)

    def get_context_vectors(self, entity: Span, doc: Doc, cui=None) -> Dict:
        """Given an entity and the document it will return the context representation for the
        given entity.

        Args:
            entity (Span): The entity to look for.
            doc (Doc): The document to look in.
            cui (Any): The CUI.

        Returns:
            Dict: The context vector.
        """
        vectors = {}
        for context_type in self.config.linking["context_vector_sizes"].keys():
            size = self.config.linking["context_vector_sizes"][context_type]
            tokens_left, tokens_center, tokens_right = self.get_context_tokens(
                entity, doc, size
            )
            values = []
            values.extend(
                [
                    self.cdb.weighted_average_function(step)
                    * self.vocab.vec(tkn.lower_)
                    for step, tkn in enumerate(tokens_left)
                    if tkn.lower_ in self.vocab
                    and self.vocab.vec(tkn.lower_) is not None
                ]
            )
            if not self.config.linking["context_ignore_center_tokens"]:
                if (
                    cui is not None
                    and random.random()
                    > self.config.linking["random_replacement_unsupervised"]
                    and self.cdb.cui2names.get(cui, [])
                ):
                    new_tokens_center = random.choice(
                        list(self.cdb.cui2names[cui])
                    ).split(self.config.general["separator"])
                    values.extend(
                        [
                            self.vocab.vec(tkn)
                            for tkn in new_tokens_center
                            if tkn in self.vocab and self.vocab.vec(tkn) is not None
                        ]
                    )
                else:
                    values.extend(
                        [
                            self.vocab.vec(tkn.lower_)
                            for tkn in tokens_center
                            if tkn.lower_ in self.vocab
                            and self.vocab.vec(tkn.lower_) is not None
                        ]
                    )
            values.extend(
                [
                    self.cdb.weighted_average_function(step)
                    * self.vocab.vec(tkn.lower_)
                    for step, tkn in enumerate(tokens_right)
                    if tkn.lower_ in self.vocab
                    and self.vocab.vec(tkn.lower_) is not None
                ]
            )
            if len(values) > 0:
                value = np.average(values, axis=0)
                vectors[context_type] = value
        return vectors

    def similarity(self, cui: str, entity: Span, doc: Doc) -> float:
        """Calculate the similarity between the learnt context for this CUI and the context
        in the given `doc`.

        Args:
            cui (str): The CUI.
            entity (Span): The entity to look for.
            doc (Doc): The document to look in.

        Returns:
            float: The similarity.
        """
        vectors = self.get_context_vectors(entity, doc)
        sim = self._similarity(cui, vectors)
        return sim

    def _similarity(self, cui: str, vectors: Dict) -> float:
        """Calculate similarity once we have vectors and a cui.

        Args:
            cui (str): The CUI.
            vectors (Dict): The vectors.

        Returns:
            float: The similarity.
        """
        cui_vectors = self.cdb.cui2context_vectors.get(cui, {})
        if (
            cui_vectors
            and self.cdb.cui2count_train[cui]
            >= self.config.linking["train_count_threshold"]
        ):
            similarity = 0
            for context_type in self.config.linking["context_vector_weights"]:
                if context_type in vectors and context_type in cui_vectors:
                    weight = self.config.linking["context_vector_weights"][context_type]
                    s = np.dot(
                        unitvec(vectors[context_type]),
                        unitvec(cui_vectors[context_type]),
                    )
                    similarity += weight * s
                    logger.debug(
                        "Similarity for CUI: %s, Count: %s, Context Type: %.10s, Weight: %s.2f, Similarity: %s.3f, S*W: %s.3f",
                        cui,
                        self.cdb.cui2count_train[cui],
                        context_type,
                        weight,
                        s,
                        s * weight,
                    )
            return similarity
        else:
            return -1

    def disambiguate(self, cuis: List, entity: Span, name: str, doc: Doc) -> Tuple:
        vectors = self.get_context_vectors(entity, doc)
        filters = self.config.linking["filters"]
        if self.config.linking["filter_before_disamb"]:
            logger.debug("Is trainer, subsetting CUIs")
            logger.debug("CUIs before: %s", cuis)
            cuis = [cui for cui in cuis if filters.check_filters(cui)]
            logger.debug("CUIs after: %s", cuis)
        if cuis:
            similarities = [self._similarity(cui, vectors) for cui in cuis]
            logger.debug(
                "Similarities: %s", [(sim, cui) for sim, cui in zip(cuis, similarities)]
            )
            if self.config.linking.get("prefer_primary_name", 0) > 0:
                logger.debug("Preferring primary names")
                for i, cui in enumerate(cuis):
                    if similarities[i] > 0 and self.cdb.name2cuis2status.get(
                        name, {}
                    ).get(cui, "") in {"P", "PD"}:
                        old_sim = similarities[i]
                        similarities[i] = min(
                            0.99,
                            similarities[i]
                            + similarities[i]
                            * self.config.linking.get("prefer_primary_name", 0),
                        )
                        logger.debug(
                            "CUI: %s, Name: %s, Old sim: %.3f, New sim: %.3f",
                            cui,
                            name,
                            old_sim,
                            similarities[i],
                        )
            if self.config.linking.get("prefer_frequent_concepts", 0) > 0:
                logger.debug("Preferring frequent concepts")
                cnts = [self.cdb.cui2count_train.get(cui, 0) for cui in cuis]
                m = min(cnts) if min(cnts) > 0 else 1
                scales = [
                    np.log10(cnt / m)
                    * self.config.linking.get("prefer_frequent_concepts", 0)
                    if cnt > 10
                    else 0
                    for cnt in cnts
                ]
                similarities = [
                    min(0.99, sim + sim * scales[i])
                    for i, sim in enumerate(similarities)
                ]
            mx = np.argmax(similarities)
            return (cuis[mx], similarities[mx])
        else:
            return (None, 0)

    # def train(
    #     self,
    #     cui: str,
    #     entity: Span,
    #     doc: Doc,
    #     negative: bool = False,
    #     names: Union[List[str], Dict] = [],
    # ) -> None:
    #     """Update the context representation for this CUI, given it's correct location (entity)
    #     in a document (doc).

    #     Args:
    #         cui (str): The CUI to train.
    #         entity (Span): The entity we're at.
    #         doc (Doc): The document within which we're working.
    #         negative (bool): Whether or not the example is negative. Defaults to False.
    #         names (List[str]/Dict):
    #             Optionally used to update the `status` of a name-cui pair in the CDB.
    #     """
    #     if len(entity) > 0:
    #         vectors = self.get_context_vectors(entity, doc, cui=cui)
    #         self.cdb.update_context_vector(cui=cui, vectors=vectors, negative=negative)
    #         logger.debug("Updating CUI: %s with negative=%s", cui, negative)
    #         if not negative:
    #             if type(entity) is Span:
    #                 self.cdb.name2count_train[entity._.detected_name] = (
    #                     self.cdb.name2count_train.get(entity._.detected_name, 0) + 1
    #                 )
    #             if self.config.linking.get("calculate_dynamic_threshold", False):
    #                 sim = self.similarity(cui, entity, doc)
    #                 self.cdb.update_cui2average_confidence(cui=cui, new_sim=sim)
    #         if negative:
    #             for name in names:
    #                 if self.cdb.name2cuis2status.get(name, {}).get(cui, "") == "P":
    #                     self.cdb.name2cuis2status.get(name, {})[cui] = "PD"
    #                     logger.debug(
    #                         "Updating status for CUI: %s, name: %s to <PD>", cui, name
    #                     )
    #                 elif self.cdb.name2cuis2status.get(name, {}).get(cui, "") == "A":
    #                     self.cdb.name2cuis2status.get(name, {})[cui] = "N"
    #                     logger.debug(
    #                         "Updating status for CUI: %s, name: %s to <N>", cui, name
    #                     )
    #         if negative or self.config.linking.get("devalue_linked_concepts", False):
    #             _cuis = set()
    #             for name in self.cdb.cui2names[cui]:
    #                 _cuis.update(self.cdb.name2cuis.get(name, []))
    #             _cuis = _cuis - {cui}
    #             for _cui in _cuis:
    #                 self.cdb.update_context_vector(
    #                     cui=_cui, vectors=vectors, negative=True
    #                 )
    #             logger.debug(
    #                 "Devalued via names.\n\tBase cui: %s \n\tTo be devalued: %s\n",
    #                 cui,
    #                 _cuis,
    #             )
    #     else:
    #         logger.warning(
    #             "The provided entity for cui <%s> was empty, nothing to train", cui
    #         )

    # def train_using_negative_sampling(self, cui: str) -> None:
    #     vectors = {}
    #     for context_type in self.config.linking["context_vector_sizes"].keys():
    #         size = self.config.linking["context_vector_sizes"][context_type]
    #         inds = self.vocab.get_negative_samples(
    #             size,
    #             ignore_punct_and_num=self.config.linking[
    #                 "negative_ignore_punct_and_num"
    #             ],
    #         )
    #         values = [self.vocab.vec(self.vocab.index2word[ind]) for ind in inds]
    #         if len(values) > 0:
    #             vectors[context_type] = np.average(values, axis=0)
    #         logger.debug("Updating CUI: %s, with %s negative words", cui, len(inds))
    #     self.cdb.update_context_vector(cui=cui, vectors=vectors, negative=True)


class LinkingFilters:
    def __init__(self, config: dict):
        self.config = config

    def check_filters(self, cui: str) -> bool:
        return
