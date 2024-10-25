from typing import Dict, Iterable, Optional, Set

from healthchain.pipeline.models.medcatlite.configs import Config


class NorvigSpellChecker:
    """
    A spell checker implementation based on Peter Norvig's algorithm.

    This class provides methods for spell checking and correction using a probabilistic approach
    based on word frequencies.

    Attributes:
        word_frequency (Dict[str, int]): A dictionary of words and their frequencies.
        config (Dict[str, Any]): Configuration settings for the spell checker.

    Methods:
        fix(word: str) -> Optional[str]:
            Finds the most probable spelling correction for a given word.

        candidates(word: str) -> Set[str]:
            Generates possible spelling corrections for a given word.

        known(words: Iterable[str]) -> Set[str]:
            Returns the subset of words that appear in the vocabulary.

        edits1(word: str) -> Set[str]:
            Generates all possible edits that are one edit away from the given word.

        edits2(word: str) -> Set[str]:
            Generates all possible edits that are two edits away from the given word.

        _probability(word: str) -> float:
            Calculates the probability of a word based on its frequency.
    """

    def __init__(self, word_frequency: Dict[str, int], config: Config):
        """
        Initialize the NorvigSpellChecker.

        Args:
            word_frequency (Dict[str, int]): A dictionary of words and their frequencies.
            config (Dict[str, Any]): Configuration settings for the spell checker.

        The word_frequency dictionary is used to calculate word probabilities for spell checking.
        The config dictionary contains various settings that control the behavior of the spell checker.
        """
        # TODO: make the config general - not medcat specific so can be used across modules
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

        if self.config.general.spell_check_deep:
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
        if self.config.general.diacritics:
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
