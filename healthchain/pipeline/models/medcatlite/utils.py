# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


from collections import defaultdict
import logging
import json
import shutil
import pickle
import numpy as np
from typing import (
    Dict,
    Set,
    Optional,
    List,
    Type,
    Union,
    Any,
)
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
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
    zip_path = Path(zip_path)
    base_dir = zip_path.parent
    foldername = zip_path.stem
    model_pack_path = base_dir / foldername

    if model_pack_path.exists():
        logger.info(
            f"Found an existing unzipped model pack at: {model_pack_path}, the provided zip will not be touched."
        )
    else:
        logger.info("Unzipping the model pack and loading models.")
        shutil.unpack_archive(str(zip_path), extract_dir=str(model_pack_path))

    return str(model_pack_path)


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


def weighted_average(step: int, factor: float) -> float:
    return max(0.1, 1 - step**2 * factor)


def default_weighted_average(step: int) -> float:
    return weighted_average(step, factor=0.0004)


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
    separator: str = "~"
    workers: int = 4
    diacritics: bool = False
    spell_check_deep: bool = False
    spell_check_len_limit: int = 7
    make_pretty_labels: Optional[str] = None  # None or "long" or "short"
    map_cui_to_group: bool = False


class NERConfig(BaseModel):
    min_name_len: int = 3
    max_skip_tokens: int = 2
    try_reverse_word_order: bool = False
    check_upper_case_names: bool = False
    upper_case_limit_len: int = 4


class LinkingConfig(BaseModel):
    train_count_threshold: int = 1
    similarity_threshold_type: str = "static"
    similarity_threshold: float = 0.25
    context_vector_sizes: Dict[str, int] = Field(
        default_factory=lambda: {"long": 18, "medium": 9, "short": 3}
    )
    context_vector_weights: Dict[str, float] = Field(
        default_factory=lambda: {"long": 0.5, "medium": 0.3, "short": 0.2}
    )
    context_ignore_center_tokens: bool = False
    random_replacement_unsupervised: float = 0.80
    filter_before_disamb: bool = False
    prefer_primary_name: float = 0.35
    prefer_frequent_concepts: float = 0.35
    disamb_length_limit: int = 3
    always_calculate_similarity: bool = False


class PreprocessingConfig(BaseModel):
    words_to_skip: set = {"nos"}
    keep_punct: set = {".", ":"}
    do_not_normalize: set = {"VBD", "VBG", "VBN", "VBP", "JJS", "JJR"}
    skip_stopwords: bool = False
    min_len_normalize: int = 5
    stopwords: Optional[set] = None


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
            json.dump(self.model_dump(), f, indent=2)


class CDB:
    def __init__(self, config: Union[Config, None] = None):
        self.config = config or Config()
        self.name2cuis2status = {}
        self.cui2average_confidence = {}
        self.addl_info = {}
        self.snames = set()
        self.cui2snames: Dict[str, Set[str]] = defaultdict(set)
        self.cui2names: Dict[str, Set[str]] = defaultdict(set)
        self.cui2context_vectors = {}
        self.cui2count_train = {}
        self.name2count_train = {}
        self.name_isupper: Dict = {}
        self.vocab = {}
        self.weighted_average_function = default_weighted_average

    def __repr__(self):
        return (
            f"CDB(\n"
            f"    config:                 {self.config}\n"
            f"    name2cuis2status:       {self._preview_dict(self.name2cuis2status)}\n"
            f"    cui2average_confidence: {self._preview_dict(self.cui2average_confidence)}\n"
            f"    addl_info:              {self._preview_dict(self.addl_info, preview_type=True)}\n"
            f"    snames:                 {self._preview_set(self.snames)}\n"
            f"    cui2snames:             {self._preview_dict(self.cui2snames, n=1)}\n"
            f"    cui2names:              {self._preview_dict(self.cui2names, n=1)}\n"
            f"    cui2context_vectors:    {self._preview_dict(self.cui2context_vectors, preview_type=True)}\n"
            f"    cui2count_train:        {self._preview_dict(self.cui2count_train)}\n"
            f"    name2count_train:       {self._preview_dict(self.name2count_train)}\n"
            f"    name_isupper:           {self._preview_dict(self.name_isupper)}\n"
            f"    vocab:                  {self._preview_dict(self.vocab)}\n"
            f"    weighted_average_function: {self.weighted_average_function}\n"
            f")"
        )

    def _preview_dict(self, d, n=3, preview_type=False):
        """
        Generate a preview of a dictionary.

        Args:
            d (dict): The dictionary to preview.
            n (int): The number of items to include in the preview.
            preview_type (bool): Whether to show the type of values instead of the values themselves.

        Returns:
            str: A string representation of the dictionary preview.
        """
        items = list(d.items())[:n]
        if preview_type:
            items = [(k, type(v)) for k, v in items]
        preview = dict(items)
        return f"{preview}, (total: {len(d)})"

    def _preview_set(self, s, n=3):
        return f"{set(list(s)[:n])}, (total: {len(s)})"

    @classmethod
    def load(cls, path: str) -> "CDB":
        # Removed weighted_average_function fix - only use default
        cdb = deserialize_cdb(path, cls)
        return cdb


class Vocab:
    """
    A class to manage vocabulary and word vectors, with optional memory mapping support.

    Attributes:
        vocab (dict): A dictionary mapping words to their vector indices or full vectors.
        use_memory_mapping (bool): Whether to use memory mapping for efficient vector loading.
        _vector_file (file): The file object for memory-mapped vector data.
        _vector_shape (tuple): The shape of the vector array.

    Methods:
        __init__(self, use_memory_mapping: bool = False)
        __repr__(self)
        _preview_dict(self, d, n=3, preview_type=False)
        create_vector_files(cls, model_pack_path: str, force_recreate: bool = False)
        load(cls, path: str, use_memory_mapping: bool = False) -> 'Vocab'
        vec(self, word: str) -> Optional[np.ndarray]
        __del__(self)
    """

    def __init__(self, use_memory_mapping: bool = False):
        """
        Initialize the Vocab object.

        Args:
            use_memory_mapping (bool): Whether to use memory mapping for efficient vector loading.
        """
        self.vocab = {}
        self.use_memory_mapping = use_memory_mapping
        self._vector_file = None
        self._vector_shape = None

    def __repr__(self):
        """
        Return a string representation of the Vocab object.

        Returns:
            str: A formatted string containing information about the Vocab object.
        """
        if not self.use_memory_mapping:
            preview_type = True
        else:
            preview_type = False

        return (
            f"Vocab(\n"
            f"    vocab:              {self._preview_dict(self.vocab, preview_type=preview_type)}\n"
            f"    use_memory_mapping: {self.use_memory_mapping}\n"
            f"    vector_shape:       {self._vector_shape}\n"
            f")"
        )

    def _preview_dict(self, d, n=3, preview_type=False):
        """
        Generate a preview of a dictionary.

        Args:
            d (dict): The dictionary to preview.
            n (int): The number of items to include in the preview.
            preview_type (bool): Whether to show the type of values instead of the values themselves.

        Returns:
            str: A string representation of the dictionary preview.
        """
        items = list(d.items())[:n]
        if preview_type:
            items = [(k, type(v)) for k, v in items]
        preview = dict(items)
        return f"{preview}, (total: {len(d)})"

    @classmethod
    def create_vector_files(cls, model_pack_path: str, force_recreate: bool = False):
        """
        Create optimized vector files and save them to the model pack directory.

        Args:
            model_pack_path (str): Path to the model pack directory.
            force_recreate (bool): Whether to force recreation of vector files even if they already exist.
        """
        model_path = Path(attempt_unpack(model_pack_path))
        original_vocab_path = model_path / "vocab.dat"
        output_path = model_path / "vocab"

        # Check if optimized files already exist
        mem_mapped_path = model_path / "vocab_mem_mapped.dat"
        vectors_path = model_path / "vocab.vectors"

        if not force_recreate:
            if mem_mapped_path.exists() and vectors_path.exists():
                logger.info("Optimized vector files already exist. Skipping creation.")
                return

        with open(original_vocab_path, "rb") as f:
            original_data = pickle.load(f)

        logger.debug(f"Total words in vocab: {len(original_data['vocab'])}")

        vocab = {}
        vectors = []
        new_index = 0

        for word, data in original_data["vocab"].items():
            vec = data["vec"]
            if vec is not None and isinstance(vec, np.ndarray) and vec.size > 0:
                vocab[word] = new_index
                vectors.append(vec)
                new_index += 1

        logger.debug(f"Total vectors after filtering: {len(vectors)}")

        vectors = np.array(vectors, dtype=np.float32)

        # Save vectors to a binary file
        vectors.tofile(str(vectors_path))

        # Save metadata
        metadata = {"vocab": vocab, "vector_shape": vectors.shape}
        with open(str(mem_mapped_path), "wb") as f:
            pickle.dump(metadata, f)

        logger.info(f"Vector files created in the model pack at {output_path}")

    @classmethod
    def load(cls, path: str, use_memory_mapping: bool = False) -> "Vocab":
        """
        Load a Vocab object from a file.

        Args:
            path (str): The path to the vocab file.
            use_memory_mapping (bool): Whether to use memory mapping for efficient vector loading.

        Returns:
            Vocab: A new Vocab object loaded from the file.
        """
        vocab = cls(use_memory_mapping)

        # If not memory mapped vocab will just load all the vectors for all the words
        # If memory mapped, vocab loads only word2index mapping
        with open(path, "rb") as f:
            data = pickle.load(f)
            vocab.vocab = data["vocab"]
            vocab._vector_shape = data.get("vector_shape", {})

        if use_memory_mapping:
            # Load vector file in same directory as vocab.dat
            directory = Path(path).parent
            vocab._vector_file = open(directory / "vocab.vectors", "rb")

        return vocab

    def vec(self, word: str) -> Optional[np.ndarray]:
        """
        Get the vector for a given word.

        Args:
            word (str): The word to get the vector for.

        Returns:
            Optional[np.ndarray]: The vector for the word, or None if the word is not in the vocabulary.
        """
        index = self.vocab.get(word)
        if index is None:
            return None

        if self.use_memory_mapping:
            offset = index * self._vector_shape[1] * 4  # 4 bytes per float32
            self._vector_file.seek(offset)
            vector_data = self._vector_file.read(self._vector_shape[1] * 4)
            return np.frombuffer(vector_data, dtype=np.float32)
        else:
            return self.vocab.get(word, {}).get("vec")

    def __del__(self):
        """
        Destructor method to ensure the vector file is closed when the object is deleted.
        """
        if self._vector_file:
            self._vector_file.close()


@dataclass
class CuiFilter:
    excluded_cuis: Set[str] = field(default_factory=set)

    @classmethod
    def from_txt(cls, file_path: str) -> "CuiFilter":
        """
        Initialize LinkingFilters from a plain text file containing excluded CUIs.

        Each line in the text file should contain a single CUI.

        Args:
            file_path (str): Path to the text file.

        Returns:
            LinkingFilters: An instance of LinkingFilters.
        """
        excluded_cuis = set()

        with open(file_path, "r") as txtfile:
            for line in txtfile:
                cui = line.strip()
                if cui:
                    excluded_cuis.add(cui)

        return cls(excluded_cuis=excluded_cuis)

    def check(self, cui: str) -> bool:
        return cui not in self.excluded_cuis
