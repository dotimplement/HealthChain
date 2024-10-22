# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import logging
import os
import json
import shutil
import pickle
import numpy as np
from typing import (
    Callable,
    Dict,
    Protocol,
    Set,
    Optional,
    List,
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


class LinkingFilters:
    def __init__(self, config: dict):
        self.config = config

    def check_filters(self, cui: str) -> bool:
        return
