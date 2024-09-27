import re
from dataclasses import dataclass, field
from healthchain.pipeline.components.basecomponent import Component
from healthchain.io.containers import Document
from typing import Callable, List, TypeVar, Tuple

T = TypeVar("T")


@dataclass
class TextPreprocessorConfig:
    """
    Configuration for the TextPreprocessor.

    Attributes:
        tokenizer (str): The tokenizer to use. Defaults to "basic".
        lowercase (bool): Whether to convert text to lowercase. Defaults to False.
        remove_punctuation (bool): Whether to remove punctuation. Defaults to False.
        standardize_spaces (bool): Whether to standardize spaces. Defaults to False.
        regex (List[Tuple[str, str]]): List of regex patterns and replacements. Defaults to an empty list.
    """

    tokenizer: str = "basic"
    lowercase: bool = False
    remove_punctuation: bool = False
    standardize_spaces: bool = False
    regex: List[Tuple[str, str]] = field(default_factory=list)


class TextPreprocessor(Component[str]):
    """
    A component for preprocessing text documents.

    This class applies various cleaning and tokenization steps to a Document object,
    based on the provided configuration.

    Attributes:
        config (TextPreprocessorConfig): Configuration for the preprocessor.
        tokenizer (Callable[[str], List[str]]): The tokenization function.
        cleaning_steps (List[Callable[[str], str]]): List of text cleaning functions.
    """

    def __init__(self, config: TextPreprocessorConfig = None):
        """
        Initialize the TextPreprocessor with the given configuration.

        Args:
            config (TextPreprocessorConfig, optional): Configuration for the preprocessor.
                If None, a default configuration will be used.
        """
        self.config = config or TextPreprocessorConfig()
        self.tokenizer = self._get_tokenizer(self.config.tokenizer)
        self.cleaning_steps = self._configure_cleaning_steps()

    def _get_tokenizer(self, tokenizer: str) -> Callable[[str], List[str]]:
        """
        Get the tokenization function based on the specified tokenizer.

        Args:
            tokenizer (str): The name of the tokenizer to use.

        Returns:
            Callable[[str], List[str]]: The tokenization function.

        Raises:
            ValueError: If an unsupported tokenizer is specified.
            ImportError: If the spacy tokenizer is requested but not installed.
        """
        # TODO: test import errors
        if tokenizer == "basic":
            return lambda text: text.split()
        elif tokenizer == "spacy":
            try:
                import spacy

                nlp = spacy.load("en_core_web_sm")
            except (ImportError, OSError):
                raise ImportError(
                    "To use the spacy tokenizer, please install spaCy and download the English model:\n"
                    "1. pip install spacy\n"
                    "2. python -m spacy download en_core_web_sm"
                )
            return lambda text: [token.text for token in nlp(text)]
        else:
            raise ValueError(f"Unsupported tokenizer: {tokenizer}")

    def _configure_cleaning_steps(self) -> List[Callable[[str], str]]:
        """
        Configure the text cleaning steps based on the preprocessor configuration.

        Returns:
            List[Callable[[str], str]]: List of text cleaning functions.
        """
        steps = []
        if self.config.lowercase:
            steps.append(lambda text: text.lower())

        regex_steps = []
        if self.config.regex:
            regex_steps.extend(self.config.regex)
        else:
            if self.config.remove_punctuation:
                regex_steps.append((r"[^\w\s]", ""))
            if self.config.standardize_spaces:
                regex_steps.append((r"\s+", " "))

        for pattern, repl in regex_steps:
            steps.append(self._create_regex_step(pattern, repl))

        if self.config.standardize_spaces:
            steps.append(str.strip)

        return steps

    @staticmethod
    def _create_regex_step(pattern: str, repl: str) -> Callable[[str], str]:
        """
        Create a regex-based cleaning step. This can be used in place of other cleaning steps, if required.

        Args:
            pattern (str): The regex pattern to match.
            repl (str): The replacement string.

        Returns:
            Callable[[str], str]: A function that applies the regex substitution.
        """
        return lambda text: re.sub(pattern, repl, text)

    def _clean_text(self, text: str) -> str:
        """
        Apply all cleaning steps to the input text.

        Args:
            text (str): The input text to clean.

        Returns:
            str: The cleaned text.
        """
        for step in self.cleaning_steps:
            text = step(text)
        return text

    def __call__(self, doc: Document) -> Document:
        """
        Preprocess the given Document.

        This method applies the configured cleaning steps and tokenization to the document's text (in that order).

        Args:
            doc (Document): The document to preprocess.

        Returns:
            Document: The preprocessed document with updated tokens and preprocessed text.
        """
        # Preprocess text
        preprocessed_text = self._clean_text(doc.text)

        # Tokenize
        tokens = self.tokenizer(preprocessed_text)

        # Update document
        doc.tokens = tokens
        doc.preprocessed_text = " ".join(tokens)

        return doc
