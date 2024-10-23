# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import json
import os
import logging
import spacy
from spacy.language import Language, registry
from spacy.tokens import Doc
from functools import lru_cache
from typing import Optional, List
from healthchain.pipeline.models.medcatlite.utils import (
    CDB,
    Config,
    Vocab,
    attempt_unpack,
)


logger = logging.getLogger(__name__)


class MedCATLite:
    def __init__(
        self,
        cdb: Optional[CDB] = None,
        vocab: Optional[Vocab] = None,
        config: Optional[Config] = None,
    ):
        self.config = config
        self.cdb = cdb
        self.vocab = vocab
        self.nlp = None
        self.create_pipeline()

    @classmethod
    def load_model_pack(cls, model_path: str):
        model_path = attempt_unpack(model_path)

        cdb_path = os.path.join(model_path, "cdb.dat")
        cdb = CDB.load(cdb_path)

        vocab_path = os.path.join(model_path, "vocab.dat")
        vocab = Vocab.load(vocab_path) if os.path.exists(vocab_path) else None
        config_path = (
            model_path
            if os.path.exists(os.path.join(model_path, "config.json"))
            else None
        )

        if config_path is not None:
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            config = cdb.config

        return cls(cdb, vocab, config)

    def create_pipeline(self) -> Language:
        if self.config is None:
            raise ValueError("Config not loaded. Call load_model_pack() first.")

        self.nlp = spacy.load(
            self.config.general.spacy_model,
            disable=[
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
            ],
        )

        registry.misc.register("medcatlite_vocab", func=lambda: self.vocab)
        registry.misc.register("medcatlite_cdb", func=lambda: self.cdb)

        # Add the pipe component
        self.nlp.add_pipe(
            "medcatlite_token_processor",
            config={
                "token_processor_resources": {
                    "@misc": "medcatlite.token_processor_resources",
                    "cdb": {"@misc": "medcatlite_cdb"},
                    "vocab": {"@misc": "medcatlite_vocab"},
                }
            },
            first=True,
        )

        # self.nlp.add_pipe('medcat_ner', last=True)

        # self.nlp.add_pipe('medcat_linker', config={'cdb': self.cdb, 'vocab': self.vocab, 'config': self.config})

        return self.nlp

    @lru_cache(maxsize=1000)
    def process(self, text: str) -> "Doc":
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")
        return self.nlp(text)

    def batch_process(self, texts: List[str], batch_size: int = 32) -> List["Doc"]:
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")
        return list(self.nlp.pipe(texts, batch_size=batch_size))

    def save_pipeline(self, path: str):
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")
        self.nlp.to_disk(path)
