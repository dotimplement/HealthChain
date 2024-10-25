# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import logging
from spacy.language import Language
from spacy.tokens import Doc, Span, Token
from typing import Any, Dict, List, Tuple, Optional

from healthchain.pipeline.models.medcatlite.configs import Config
from healthchain.pipeline.models.medcatlite.utils import CDB

logger = logging.getLogger(__name__)


@Language.factory("medcatlite_ner")
def create_ner(nlp: Language, name: str, ner_resources: Dict[str, Any]):
    return NER(nlp, name, ner_resources)


class NER:
    def __init__(self, nlp: Language, name: str, ner_resources: Dict[str, Any]):
        """
        Initialize the NER class.

        Args:
            nlp (Language): The spaCy language object.
            name (str): The name of the component.
            cdb (CDB): The concept database.
            config (Config): The configuration object.
        """
        self.nlp = nlp
        self.name = name
        self.cdb: CDB = ner_resources["cdb"]
        self.config: Config = ner_resources["config"]
        self._setup_extensions()

    def _setup_extensions(self):
        """
        Set up custom extensions for Doc, Token, and Span objects.
        """
        # Set up custom extensions for Doc objects
        if not Doc.has_extension("ents"):
            Doc.set_extension("ents", default=[])

        # Set up custom extensions for Span objects
        span_extensions = {
            "confidence": -1,
            "id": 0,
            "link_candidates": None,
            "detected_name": None,
        }

        for name, default_value in span_extensions.items():
            if not Span.has_extension(name):
                Span.set_extension(name, default=default_value)

    def __call__(self, doc: Doc) -> Doc:
        """
        Process the document to identify named entities.

        Args:
            doc (Doc): The spaCy document object.

        Returns:
            Doc: The processed document with identified entities.
        """
        tokens_to_process = [tkn for tkn in doc if not tkn._.to_skip]
        for i in range(len(tokens_to_process)):
            self.process_token(doc, tokens_to_process, i)
        return doc

    def process_token(self, doc: Doc, tokens: List[Token], start_index: int):
        """
        Process a single token to identify potential named entities.

        Args:
            doc (Doc): The spaCy document object.
            tokens (List[Token]): The list of tokens in the document.
            start_index (int): The index of the token to process.
        """
        current_tokens = [tokens[start_index]]
        name = self.get_initial_name(tokens[start_index])

        if name and name in self.cdb.name2cuis and not tokens[start_index].is_stop:
            self.annotate_name(name, current_tokens, doc)

        if name:
            self._process_subsequent_tokens(
                doc, tokens, start_index, name, current_tokens
            )

    def get_initial_name(self, token: Token) -> str:
        """
        Get the initial name from the list of name versions.

        Args:
            token (Token): The token to get name versions for.

        Returns:
            str: The initial name.
        """
        name_versions = [token._.norm, token.lower_]
        return next(
            (
                name
                for name in name_versions
                if name in self.cdb.snames or name in self.cdb.name2cuis
            ),
            "",
        )

    def _process_subsequent_tokens(
        self,
        doc: Doc,
        tokens: List[Token],
        start_index: int,
        name: str,
        current_tokens: List[Token],
    ):
        """
        Process subsequent tokens to identify potential named entities.

        Args:
            doc (Doc): The spaCy document object.
            tokens (List[Token]): The list of tokens in the document.
            start_index (int): The index of the starting token.
            name (str): The initial name.
            current_tokens (List[Token]): The list of current tokens.
        """
        for j in range(start_index + 1, len(tokens)):
            if tokens[j].i - tokens[j - 1].i - 1 > self.config.ner.max_skip_tokens:
                return

            current_tokens.append(tokens[j])
            name_changed, name_reverse = self.update_name(name, tokens[j])

            if name_changed and name in self.cdb.name2cuis:
                self.annotate_name(name, current_tokens, doc)
            elif name_reverse and name_reverse in self.cdb.name2cuis:
                self.annotate_name(name_reverse, current_tokens, doc)
            else:
                break

    def update_name(self, name: str, token: Token) -> Tuple[bool, Optional[str]]:
        """
        Update the name based on the list of name versions.

        Args:
            name (str): The current name.
            token (Token): The token to get name versions for.

        Returns:
            Tuple[bool, Optional[str]]: A tuple indicating if the name was changed and the reverse name if applicable.
        """
        separator = self.config.general.separator
        name_versions = [token._.norm, token.lower_]

        for name_version in name_versions:
            new_name = f"{name}{separator}{name_version}"
            if new_name in self.cdb.snames:
                return True, None

            if self.config.ner.try_reverse_word_order:
                reverse_name = f"{name_version}{separator}{name}"
                if reverse_name in self.cdb.snames:
                    return False, reverse_name

        return False, None

    def annotate_name(
        self, name: str, tokens: List[Token], doc: Doc, label: str = "concept"
    ) -> Optional[Span]:
        """
        Annotate the identified name in the document.

        Args:
            name (str): The identified name.
            tokens (List[Token]): The list of tokens representing the name.
            doc (Doc): The spaCy document object.

        Returns:
            Optional[Span]: The annotated entity if created, None otherwise.
        """
        start, end = tokens[0].i, tokens[-1].i + 1

        if (
            self.config.ner.check_upper_case_names
            and self.cdb.name_isupper.get(name, False)
            and not all(token.is_upper for token in tokens)
        ):
            return None

        min_name_len = self.config.ner.min_name_len
        upper_case_limit_len = self.config.ner.upper_case_limit_len

        if len(name) >= min_name_len and (
            len(name) >= upper_case_limit_len
            or (len(tokens) == 1 and tokens[0].is_upper)
        ):
            if self._can_create_entity(doc, start, end):
                ent = Span(doc, start, end, label=label)
                ent._.detected_name = name
                ent._.link_candidates = self.cdb.name2cuis.get(name, [])
                ent._.id = len(doc._.ents)
                ent._.confidence = -1
                doc._.ents.append(ent)

                logger.debug(
                    "NER detected an entity.\n\tDetected name: %s\n\tLink candidates: %s\n",
                    ent._.detected_name,
                    ent._.link_candidates,
                )
                return ent

        return None

    def _can_create_entity(self, doc: Doc, start: int, end: int) -> bool:
        return len(doc.ents) == 0 or not any(
            e.start <= start < e.end or start <= e.start < end for e in doc.ents
        )
