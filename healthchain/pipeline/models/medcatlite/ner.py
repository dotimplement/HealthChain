# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import logging
from spacy.language import Language
from spacy.tokens import Doc, Span, Token
from typing import List, Tuple, Optional
from healthchain.pipeline.models.medcatlite.medcatutils import (
    CDB,
    Config,
)


logger = logging.getLogger(__name__)


@Language.factory("medcat_ner")
def create_ner(nlp: Language, name: str, cdb: CDB, config: Config):
    return NER(nlp, name, cdb, config)


class NER:
    def __init__(self, nlp: Language, name: str, cdb: CDB, config: Config):
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
        self.cdb = cdb
        self.config = config
        self._setup_extensions()

    def _setup_extensions(self):
        """
        Set up custom extensions for Doc, Token, and Span objects.
        """
        if not Doc.has_extension("to_skip"):
            Doc.set_extension("to_skip", default=False)
        if not Token.has_extension("norm"):
            Token.set_extension("norm", default="")
        if not Span.has_extension("link_candidates"):
            Span.set_extension("link_candidates", default=[])

    def __call__(self, doc: Doc) -> Doc:
        """
        Process the document to identify named entities.

        Args:
            doc (Doc): The spaCy document object.

        Returns:
            Doc: The processed document with identified entities.
        """
        tokens = list(doc)
        for i in range(len(tokens)):
            if not doc._.to_skip:
                self.process_token(doc, tokens, i)
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
        name_versions = self._get_name_versions(tokens[start_index])
        name = self.get_initial_name(name_versions)

        if name and name in self.cdb.name2cuis and not tokens[start_index].is_stop:
            self.annotate_name(name, current_tokens, doc)

        if name:
            self._process_subsequent_tokens(
                doc, tokens, start_index, name, current_tokens
            )

    def _get_name_versions(self, token: Token) -> List[str]:
        """
        Get different versions of the token's name.

        Args:
            token (Token): The token to get name versions for.

        Returns:
            List[str]: The list of name versions.
        """
        return [token._.norm, token.lower_]

    def get_initial_name(self, name_versions: List[str]) -> str:
        """
        Get the initial name from the list of name versions.

        Args:
            name_versions (List[str]): The list of name versions.

        Returns:
            str: The initial name.
        """
        for name_version in name_versions:
            if name_version in self.cdb.snames or name_version in self.cdb.name2cuis:
                return name_version
        return ""

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
            if self._exceeds_max_skip(tokens, j):
                return

            current_tokens.append(tokens[j])
            name_versions = self._get_name_versions(tokens[j])
            name_changed, name_reverse = self.update_name(name, name_versions)

            if name_changed:
                if name in self.cdb.name2cuis:
                    self.annotate_name(name, current_tokens, doc)
            elif name_reverse:
                if name_reverse in self.cdb.name2cuis:
                    self.annotate_name(name_reverse, current_tokens, doc)
            else:
                break

    def _exceeds_max_skip(self, tokens: List[Token], index: int) -> bool:
        """
        Check if the maximum number of tokens to skip is exceeded.

        Args:
            tokens (List[Token]): The list of tokens in the document.
            index (int): The current index.

        Returns:
            bool: True if the maximum number of tokens to skip is exceeded, False otherwise.
        """
        return (
            tokens[index].i - tokens[index - 1].i - 1 > self.config.ner.max_skip_tokens
        )

    def update_name(
        self, name: str, name_versions: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Update the name based on the list of name versions.

        Args:
            name (str): The current name.
            name_versions (List[str]): The list of name versions.

        Returns:
            Tuple[bool, Optional[str]]: A tuple indicating if the name was changed and the reverse name if applicable.
        """
        for name_version in name_versions:
            new_name = f"{name}{self.config.general.separator}{name_version}"
            if new_name in self.cdb.snames:
                return True, None
            if self.config.ner.get("try_reverse_word_order", False):
                reverse_name = f"{name_version}{self.config.general.separator}{name}"
                if reverse_name in self.cdb.snames:
                    return False, reverse_name
        return False, None

    def annotate_name(self, name: str, tokens: List[Token], doc: Doc):
        """
        Annotate the identified name in the document.

        Args:
            name (str): The identified name.
            tokens (List[Token]): The list of tokens representing the name.
            doc (Doc): The spaCy document object.
        """
        start, end = tokens[0].i, tokens[-1].i + 1
        if self._can_create_entity(doc, start, end):
            ent = Span(doc, start, end, label="CUSTOM")
            doc.ents = list(doc.ents) + [ent]
            ent._.set("link_candidates", self.cdb.name2cuis.get(name, []))

    def _can_create_entity(self, doc: Doc, start: int, end: int) -> bool:
        """
        Check if an entity can be created in the document.

        Args:
            doc (Doc): The spaCy document object.
            start (int): The start index of the entity.
            end (int): The end index of the entity.

        Returns:
            bool: True if an entity can be created, False otherwise.
        """
        return len(doc.ents) == 0 or not any(
            e.start <= start < e.end or start <= e.start < end for e in doc.ents
        )
