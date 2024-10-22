# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import re
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token
from typing import Dict, Any, Optional


@Language.factory("medcat_token_processor")
def create_token_processor(
    nlp: Language,
    name: str,
    config: Dict[str, Any],
    spell_checker: Optional[object] = None,
):
    return TokenProcessor(nlp, name, config, spell_checker)


class TokenProcessor:
    def __init__(
        self,
        nlp: Language,
        name: str,
        config: Dict[str, Any],
        spell_checker: Optional[object] = None,
    ):
        self.nlp = nlp
        self.config = config
        self.spell_checker = spell_checker
        self.CONTAINS_NUMBER = re.compile("\\d")
        self.punct_checker = config["preprocessing"]["punct_checker"]
        self.word_skipper = config["preprocessing"]["word_skipper"]
        self.lemmatizer = spacy.load(
            config["general"]["spacy_model"],
            disable=config["general"]["spacy_disabled_components"],
        )

        if not Token.has_extension("norm"):
            Token.set_extension("norm", default="")
        if not Token.has_extension("to_skip"):
            Token.set_extension("to_skip", default=False)
        if not Token.has_extension("is_punct"):
            Token.set_extension("is_punct", default=False)

    def __call__(self, doc: Doc) -> Doc:
        for token in doc:
            self.process_token(token)
        return doc

    def process_token(self, token: Token):
        self.tag_token(token)
        if not token._.to_skip:
            self.normalize_token(token)

    def tag_token(self, token: Token):
        cnf_p = self.config["preprocessing"]
        if (
            self.punct_checker.match(token.lower_)
            and token.text not in cnf_p["keep_punct"]
        ):
            token._.is_punct = True
            token._.to_skip = True
        else:  # inserted
            if self.word_skipper.match(token.lower_):
                token._.to_skip = True
            else:  # inserted
                if cnf_p["skip_stopwords"] and token.is_stop:
                    token._.to_skip = True

    def normalize_token(self, token: Token):
        if len(token.lower_) < self.config["preprocessing"]["min_len_normalize"]:
            token._.norm = token.lower_
        else:  # inserted
            if (
                self.config["preprocessing"]["do_not_normalize"]
                and token.tag_ is not None
                and (token.tag_ in self.config["preprocessing"]["do_not_normalize"])
            ):
                token._.norm = token.lower_
            else:  # inserted
                if token.lemma_ == "-PRON-":
                    token._.norm = token.lemma_
                    token._.to_skip = True
                else:  # inserted
                    token._.norm = token.lemma_.lower()
        if self.config["general"]["spell_check"]:
            self.apply_spell_check(token)

    def apply_spell_check(self, token: Token):
        if (
            len(token.text) >= self.config["general"]["spell_check_len_limit"]
            and (not token._.is_punct)
            and (token.lower_ not in self.spell_checker)
            and (not self.CONTAINS_NUMBER.search(token.lower_))
        ):
            fix = self.spell_checker.fix(token.lower_)
            if fix is not None:
                tmp = self.lemmatizer(fix)[0]
                if (
                    len(token.lower_)
                    < self.config["preprocessing"]["min_len_normalize"]
                ):
                    token._.norm = tmp.lower_
                else:  # inserted
                    token._.norm = tmp.lemma_.lower()
