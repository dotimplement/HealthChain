import json
from pydantic import BaseModel, Field

from typing import Dict, List, Optional


# TODO: improve - prevent hidden config options
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
