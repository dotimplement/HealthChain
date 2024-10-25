# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import json
import logging
import spacy
from spacy.language import Language, registry
from spacy.tokens import Doc
from pathlib import Path
from typing import Optional, List
from healthchain.pipeline.models.medcatlite.configs import Config
from healthchain.pipeline.models.medcatlite.utils import (
    CDB,
    CuiFilter,
    Vocab,
    attempt_unpack,
)

# ruff: noqa
from .tokenprocessor import TokenProcessor
from .ner import NER
from .linker import Linker
from .registry import (
    create_token_processor_resources,
    create_ner_resources,
    create_linker_resources,
)


logger = logging.getLogger(__name__)


class MedCATLite:
    def __init__(
        self,
        cdb: Optional[CDB] = None,
        vocab: Optional[Vocab] = None,
        config: Optional[Config] = None,
        cui_filter: Optional[CuiFilter] = None,
    ):
        """
        Initialize the MedCATLite class.

        Args:
            cdb (Optional[CDB]): The concept database.
            vocab (Optional[Vocab]): The vocabulary object.
            config (Optional[Config]): The configuration object.
            cui_filter (Optional[CuiFilter]): The CUI filter object.
        """
        self.config = config
        self.cdb = cdb
        self.vocab = vocab
        self.cui_filter = cui_filter
        self.nlp = None
        self._register_resources()
        self._create_pipeline()

    @classmethod
    def load_model_pack(cls, model_path: str, use_memory_mapping: bool = False):
        """
        Load the model pack from the specified path.

        Args:
            model_path (str): The path to the model pack.

        Returns:
            MedCATLite: An instance of the MedCATLite class.
        """
        model_path = Path(attempt_unpack(model_path))

        cdb_path = model_path / "cdb.dat"
        cdb = CDB.load(str(cdb_path))

        if use_memory_mapping:
            vocab_path = model_path / "vocab_mem_mapped.dat"
        else:
            vocab_path = model_path / "vocab.dat"
        vocab = (
            Vocab.load(str(vocab_path), use_memory_mapping)
            if vocab_path.exists()
            else None
        )

        config_path = model_path if (model_path / "config.json").exists() else None
        if config_path is not None:
            with open(config_path / "config.json", "r") as f:
                config = json.load(f)
        else:
            config = cdb.config

        return cls(cdb, vocab, config)

    def add_filter(self, cui_filter: CuiFilter):
        """
        Add a CUI filter to the pipeline.

        Args:
            cui_filter (CuiFilter): The CUI filter to add.
        """
        if "medcatlite_linker" in self.nlp.pipe_names:
            self.nlp.get_pipe("medcatlite_linker").filter = cui_filter
        else:
            logger.warning("medcatlite_linker pipe not found in the pipeline.")

    def _register_resources(self):
        """
        Register resources in the spaCy registry.
        """
        registry.misc.register("medcatlite_vocab", func=lambda: self.vocab)
        registry.misc.register("medcatlite_cdb", func=lambda: self.cdb)
        registry.misc.register("medcatlite_config", func=lambda: self.config)
        registry.misc.register("medcatlite_cui_filter", func=lambda: self.cui_filter)

    def _create_pipeline(self) -> Language:
        """
        Create the spaCy pipeline.

        Returns:
            Language: The spaCy language object.

        Raises:
            ValueError: If the configuration is not loaded.
        """
        if self.config is None:
            raise ValueError("Config not loaded. Call load_model_pack() first.")

        self.nlp = spacy.load(
            self.config.general.spacy_model,
            disable=self.config.general.spacy_disabled_components,
        )

        self.nlp.add_pipe(
            "medcatlite_token_processor",
            config={
                "token_processor_resources": {
                    "@misc": "medcatlite.token_processor_resources",
                    "cdb": {"@misc": "medcatlite_cdb"},
                    "config": {"@misc": "medcatlite_config"},
                }
            },
        )

        self.nlp.add_pipe(
            "medcatlite_ner",
            config={
                "ner_resources": {
                    "@misc": "medcatlite.ner_resources",
                    "cdb": {"@misc": "medcatlite_cdb"},
                    "config": {"@misc": "medcatlite_config"},
                }
            },
        )

        self.nlp.add_pipe(
            "medcatlite_linker",
            config={
                "linker_resources": {
                    "@misc": "medcatlite.linker_resources",
                    "cdb": {"@misc": "medcatlite_cdb"},
                    "vocab": {"@misc": "medcatlite_vocab"},
                    "config": {"@misc": "medcatlite_config"},
                    "cui_filter": {"@misc": "medcatlite_cui_filter"},
                }
            },
        )

        return self.nlp

    def process(self, text: str) -> "Doc":
        """
        Process a single text document.

        Args:
            text (str): The text to process.

        Returns:
            Doc: The processed spaCy document.

        Raises:
            ValueError: If the pipeline is not created.
        """
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")

        return self.nlp(text)

    def batch_process(self, texts: List[str], batch_size: int = 32) -> List["Doc"]:
        """
        Process a batch of text documents.

        Args:
            texts (List[str]): The list of texts to process.
            batch_size (int, optional): The batch size. Defaults to 32.

        Returns:
            List[Doc]: The list of processed spaCy documents.

        Raises:
            ValueError: If the pipeline is not created.
        """
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")

        return list(self.nlp.pipe(texts, batch_size=batch_size))

    def save_pipeline(self, path: str):
        """
        Save the spaCy pipeline to disk.

        Args:
            path (str): The path to save the pipeline.

        Raises:
            ValueError: If the pipeline is not created.
        """
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")

        self.nlp.to_disk(path)
