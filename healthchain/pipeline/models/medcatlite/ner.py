# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import logging
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span, Token
from typing import Optional, List, Tuple
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
        self.nlp = nlp
        self.name = name
        self.cdb = cdb
        self.config = config

        if not Doc.has_extension("to_skip"):
            Doc.set_extension("to_skip", default=False)
        if not Token.has_extension("norm"):
            Token.set_extension("norm", default="")
        if not Span.has_extension("link_candidates"):
            Span.set_extension("link_candidates", default=[])

    def process_token(
        self, doc: Doc, tokens: List[spacy.tokens.Token], start_index: int
    ):
        current_tokens = [tokens[start_index]]
        name_versions = [tokens[start_index]._.norm, tokens[start_index].lower_]
        name = self.get_initial_name(name_versions)
        if name and name in self.cdb.name2cuis and (not tokens[start_index].is_stop):
            self.annotate_name(name, current_tokens, doc)
        if name:
            for j in range(start_index + 1, len(tokens)):
                if tokens[j].i - tokens[j - 1].i - 1 > self.config.ner.max_skip_tokens:
                    return
                current_tokens.append(tokens[j])
                name_versions = [tokens[j]._.norm, tokens[j].lower_]
                name_changed, name_reverse = self.update_name(name, name_versions)
                if name_changed:
                    if name in self.cdb.name2cuis:
                        self.annotate_name(name, current_tokens, doc)
                else:  # inserted
                    if name_reverse:
                        if name_reverse in self.cdb.name2cuis:
                            self.annotate_name(name_reverse, current_tokens, doc)
                    else:  # inserted
                        break

    def get_initial_name(self, name_versions: List[str]) -> str:
        for name_version in name_versions:
            if name_version in self.cdb.snames:
                return name_version
            if name_version in self.cdb.name2cuis:
                return name_version
        else:
            return ""

    def update_name(
        self, name: str, name_versions: List[str]
    ) -> Tuple[bool, Optional[str]]:
        for name_version in name_versions:
            new_name = name + self.config.general.separator + name_version
            if new_name in self.cdb.snames:
                return (True, None)
            if self.config.ner.get("try_reverse_word_order", False):
                reverse_name = name_version + self.config.general.separator + name
                if reverse_name in self.cdb.snames:
                    return (False, reverse_name)
        else:
            return (False, None)

    def annotate_name(self, name: str, tokens: List[spacy.tokens.Token], doc: Doc):
        start = tokens[0].i
        end = tokens[(-1)].i + 1
        # span = doc[start:end]
        if len(doc.ents) == 0 or not any(
            (e.start <= start < e.end or start <= e.start < end for e in doc.ents)
        ):
            ent = Span(doc, start, end, label="CUSTOM")
            doc.ents = list(doc.ents) + [ent]
            ent._.set("link_candidates", self.cdb.name2cuis.get(name, []))
