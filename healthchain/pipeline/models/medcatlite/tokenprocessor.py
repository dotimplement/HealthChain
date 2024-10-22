# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


import re
from spacy.language import Language
from spacy.tokens import Doc, Token
from typing import Dict, Any, Iterable, Optional, Set


class BasicSpellChecker(object):
    def __init__(self, cdb_vocab, config, data_vocab=None):
        self.vocab = cdb_vocab
        self.config = config
        self.data_vocab = data_vocab

    def P(self, word: str) -> float:
        """Probability of `word`.

        Args:
            word (str): The word in question.

        Returns:
            float: The probability.
        """
        cnt = self.vocab.get(word, 0)
        if cnt != 0:
            return -1 / cnt
        return 0

    def __contains__(self, word):
        if word in self.vocab:
            return True
        if self.data_vocab is not None and word in self.data_vocab:
            return False
        return False

    def fix(self, word: str) -> Optional[str]:
        """Most probable spelling correction for word.

        Args:
            word (str): The word.

        Returns:
            Optional[str]: Fixed word, or None if no fixes were applied.
        """
        fix = max(self.candidates(word), key=self.P)
        if fix != word:
            return fix
        return None

    def candidates(self, word: str) -> Iterable[str]:
        """Generate possible spelling corrections for word.

        Args:
            word (str): The word.

        Returns:
            Iterable[str]: The list of candidate words.
        """
        if self.config.general.spell_check_deep:
            return (
                self.known([word])
                or self.known(self.edits1(word))
                or self.known(self.edits2(word))
                or [word]
            )
        return self.known([word]) or self.known(self.edits1(word)) or [word]

    def known(self, words: Iterable[str]) -> Set[str]:
        """The subset of `words` that appear in the dictionary of WORDS.

        Args:
            words (Iterable[str]): The words.

        Returns:
            Set[str]: The set of candidates.
        """
        return set((w for w in words if w in self.vocab))

    def edits1(self, word: str) -> Set[str]:
        return self.get_edits1(word, self.config.general.diacritics)


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
        """
        Initialize the TokenProcessor class.

        Args:
            nlp (Language): The spaCy language object.
            name (str): The name of the component.
            config (Dict[str, Any]): The configuration dictionary.
            spell_checker (Optional[object]): The spell checker object, if any.
        """
        self.nlp = nlp
        self.config = config
        self.spell_checker = spell_checker
        self._setup_regex_patterns()
        self._setup_token_extensions()
        self._setup_lemmatizer()

    def _setup_regex_patterns(self):
        """
        Set up regular expression patterns for token processing.
        """
        self.CONTAINS_NUMBER = re.compile(r"\d")
        self.punct_checker = self.config["preprocessing"]["punct_checker"]
        self.word_skipper = self.config["preprocessing"]["word_skipper"]

    def _setup_token_extensions(self):
        """
        Set up custom extensions for Token objects.
        """
        for ext in ["norm", "to_skip", "is_punct"]:
            if not Token.has_extension(ext):
                Token.set_extension(ext, default="" if ext == "norm" else False)

    def _setup_lemmatizer(self):
        """
        Set up the lemmatizer component.
        """
        if not self.nlp.has_pipe("lemmatizer"):
            self.lemmatizer = self.nlp.create_pipe("lemmatizer")
        else:
            self.lemmatizer = self.nlp.get_pipe("lemmatizer")

    def __call__(self, doc: Doc) -> Doc:
        """
        Process the document to apply token processing.

        Args:
            doc (Doc): The spaCy document object.

        Returns:
            Doc: The processed document.
        """
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
        """
        Check if spell check should be applied to the token.

        Args:
            token (Token): The token to check.

        Returns:
            bool: True if spell check should be applied, False otherwise.
        """
        return (
            len(token.text) >= self.config["general"]["spell_check_len_limit"]
            and not token._.is_punct
            and token.lower_ not in self.spell_checker
            and not self.CONTAINS_NUMBER.search(token.lower_)
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
