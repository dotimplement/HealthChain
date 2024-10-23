# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0

import logging
import re
from spacy.language import Language
from spacy.tokens import Doc, Token
from typing import Dict, Any, Iterable, Optional, Set


log = logging.getLogger(__name__)


class NorvigSpellChecker:
    def __init__(self, word_frequency: Dict[str, int], config: Dict[str, Any]):
        self.word_frequency = word_frequency
        self.config = config

    def fix(self, word: str) -> Optional[str]:
        """Most probable spelling correction for word."""
        candidates = self.candidates(word)
        best_candidate = max(candidates, key=self._probability)
        return best_candidate if best_candidate != word else None

    def candidates(self, word: str) -> Set[str]:
        """Generate possible spelling corrections for word."""
        known_words = self.known([word])
        if known_words:
            return known_words

        edit1_words = self.known(self.edits1(word))
        if edit1_words:
            return edit1_words

        if self.config["general"]["spell_check_deep"]:
            edit2_words = self.known(self.edits2(word))
            if edit2_words:
                return edit2_words

        return {word}

    def known(self, words: Iterable[str]) -> Set[str]:
        """The subset of words that appear in the vocabulary."""
        return {w for w in words if w in self.word_frequency}

    def edits1(self, word: str) -> Set[str]:
        """All edits that are one edit away from word."""
        letters = "abcdefghijklmnopqrstuvwxyz"
        if self.config["general"]["diacritics"]:
            letters += "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"

        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = {L + R[1:] for L, R in splits if R}
        transposes = {L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1}
        replaces = {L + c + R[1:] for L, R in splits if R for c in letters}
        inserts = {L + c + R for L, R in splits for c in letters}

        return deletes | transposes | replaces | inserts

    def edits2(self, word: str) -> Set[str]:
        """All edits that are two edits away from word."""
        return {e2 for e1 in self.edits1(word) for e2 in self.edits1(e1)}

    def _probability(self, word: str) -> float:
        """Probability of word."""
        count = self.word_frequency.get(word, 0)
        return -1 / count if count else 0


@Language.factory("medcatlite_token_processor")
def create_token_processor(
    nlp: Language, name: str, token_processor_resources: Dict[str, Any]
):
    return TokenProcessor(nlp, name, token_processor_resources)


class TokenProcessor:
    def __init__(
        self, nlp: Language, name: str, token_processor_resources: Dict[str, Any]
    ):
        self.nlp = nlp
        self.name = name
        self.config = token_processor_resources["config"]
        self.cdb_word_freq = token_processor_resources["cdb_word_freq"]
        self.spell_checker = NorvigSpellChecker(
            word_frequency=self.cdb_word_freq, config=self.config
        )
        self._setup_regex_patterns()
        self._setup_token_extensions()
        self._setup_nlp_components()

    def _setup_regex_patterns(self):
        """
        Set up regular expression patterns for token processing.
        """
        self.contains_number = re.compile(r"\d")
        self.punct_checker = re.compile(r"[^a-z0-9]+")
        self.word_skipper = re.compile(
            "^({})$".format("|".join(self.config["preprocessing"]["words_to_skip"]))
        )

    def _setup_token_extensions(self):
        """
        Set up custom extensions for Token objects.
        """
        for ext in ["norm", "to_skip", "is_punct"]:
            if not Token.has_extension(ext):
                Token.set_extension(ext, default="" if ext == "norm" else False)

    def _setup_nlp_components(self):
        """
        Set up the lemmatizer, tagger, and attribute ruler components.
        """
        if not self.nlp.has_pipe("lemmatizer"):
            self.lemmatizer = self.nlp.add_pipe("lemmatizer")
        else:
            self.lemmatizer = self.nlp.get_pipe("lemmatizer")

        if not self.nlp.has_pipe("tagger"):
            self.tagger = self.nlp.add_pipe("tagger")
        else:
            self.tagger = self.nlp.get_pipe("tagger")

        if not self.nlp.has_pipe("attribute_ruler"):
            self.attribute_ruler = self.nlp.add_pipe("attribute_ruler")
        else:
            self.attribute_ruler = self.nlp.get_pipe("attribute_ruler")

    def __call__(self, doc: Doc) -> Doc:
        """
        Process the document to apply token processing.

        Args:
            doc (Doc): The spaCy document object.

        Returns:
            Doc: The processed document.
        """
        self.tagger(doc)
        self.attribute_ruler(doc)
        self.lemmatizer(doc)
        for token in doc:
            self.process_token(token)
        return doc

    def process_token(self, token: Token):
        """
        Process a single token.

        Args:
            token (Token): The token to process.
        """
        self._tag_token(token)
        if not token._.to_skip:
            self._normalize_token(token)

    def _tag_token(self, token: Token):
        """
        Tag the token based on its properties.

        Args:
            token (Token): The token to tag.
        """
        cnf_p = self.config["preprocessing"]
        if self._is_punctuation(token, cnf_p):
            token._.is_punct = True
            token._.to_skip = True
        elif self._should_skip_token(token, cnf_p):
            token._.to_skip = True

    def _is_punctuation(self, token: Token, cnf_p: Dict) -> bool:
        """
        Check if the token is punctuation.

        Args:
            token (Token): The token to check.
            cnf_p (Dict): The preprocessing configuration dictionary.

        Returns:
            bool: True if the token is punctuation, False otherwise.
        """
        return (
            self.punct_checker.match(token.lower_)
            and token.text not in cnf_p["keep_punct"]
        )

    def _should_skip_token(self, token: Token, cnf_p: Dict) -> bool:
        """
        Check if the token should be skipped.

        Args:
            token (Token): The token to check.
            cnf_p (Dict): The preprocessing configuration dictionary.

        Returns:
            bool: True if the token should be skipped, False otherwise.
        """
        return self.word_skipper.match(token.lower_) or (
            cnf_p["skip_stopwords"] and token.is_stop
        )

    def _normalize_token(self, token: Token):
        """
        Normalize the token.

        Args:
            token (Token): The token to normalize.
        """
        if len(token.lower_) < self.config["preprocessing"]["min_len_normalize"]:
            token._.norm = token.lower_
        else:
            token._.norm = self._get_normalized_form(token)

        if self.config["general"]["spell_check"]:
            self._apply_spell_check(token)

    def _get_normalized_form(self, token: Token) -> str:
        """
        Get the normalized form of the token.

        Args:
            token (Token): The token to normalize.

        Returns:
            str: The normalized form of the token.
        """
        if self._should_not_normalize(token):
            return token.lower_
        elif token.lemma_ == "-PRON-":
            token._.to_skip = True
            return token.lemma_
        else:
            return token.lemma_.lower()

    def _should_not_normalize(self, token: Token) -> bool:
        """
        Check if the token should not be normalized.

        Args:
            token (Token): The token to check.

        Returns:
            bool: True if the token should not be normalized, False otherwise.
        """
        return (
            self.config["preprocessing"]["do_not_normalize"]
            and token.tag_ is not None
            and (token.tag_ in self.config["preprocessing"]["do_not_normalize"])
        )

    def _apply_spell_check(self, token: Token):
        """
        Apply spell check to the token.

        Args:
            token (Token): The token to spell check.
        """
        if self._should_apply_spell_check(token):
            fix = self.spell_checker.fix(token.lower_)
            if fix is not None:
                self._apply_spell_fix(token, fix)

    def _should_apply_spell_check(self, token: Token) -> bool:
        return (
            len(token.text) >= self.config["general"]["spell_check_len_limit"]
            and not token._.is_punct
            and token.lower_ not in self.spell_checker.word_frequency
            and not self.contains_number.search(token.lower_)
        )

    def _apply_spell_fix(self, token: Token, fix: str):
        """
        Apply the spell fix to the token.

        Args:
            token (Token): The token to fix.
            fix (str): The fixed token text.
        """
        tmp = self.nlp(fix)[0]
        if len(token.lower_) < self.config["preprocessing"]["min_len_normalize"]:
            token._.norm = tmp.lower_
        else:
            token._.norm = tmp.lemma_.lower()
