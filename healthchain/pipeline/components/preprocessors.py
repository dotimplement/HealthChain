import re
from healthchain.pipeline.components.base import BaseComponent
from healthchain.io.containers import Document
from typing import Callable, List, TypeVar, Tuple, Union

T = TypeVar("T")


class TextPreProcessor(BaseComponent[Document]):
    """
    A component for preprocessing text documents.

    This class applies various cleaning and tokenization steps to a Document object,
    based on the provided configuration.

    Attributes:
        tokenizer (Union[str, Callable[[str], List[str]]]): The tokenizer to use. Can be "basic" or a custom
            tokenization function that takes a string and returns a list of tokens. Defaults to "basic".
        lowercase (bool): Whether to convert text to lowercase. Defaults to False.
        remove_punctuation (bool): Whether to remove punctuation. Defaults to False.
        standardize_spaces (bool): Whether to standardize spaces. Defaults to False.
        regex (List[Tuple[str, str]]): List of regex patterns and replacements. Defaults to an empty list.
        tokenizer_func (Callable[[str], List[str]]): The tokenization function.
        cleaning_steps (List[Callable[[str], str]]): List of text cleaning functions.
    """

    def __init__(
        self,
        tokenizer: Union[str, Callable[[str], List[str]]] = "basic",
        lowercase: bool = False,
        remove_punctuation: bool = False,
        standardize_spaces: bool = False,
        regex: List[Tuple[str, str]] = None,
    ):
        """
        Initialize the TextPreprocessor with the given configuration.

        Args:
            tokenizer (Union[str, Callable[[str], List[str]]]): The tokenizer to use. Can be "basic" or a custom
                tokenization function that takes a string and returns a list of tokens. Defaults to "basic".
            lowercase (bool): Whether to convert text to lowercase. Defaults to False.
            remove_punctuation (bool): Whether to remove punctuation. Defaults to False.
            standardize_spaces (bool): Whether to standardize spaces. Defaults to False.
            regex (List[Tuple[str, str]], optional): List of regex patterns and replacements. Defaults to None.
        """
        self.lowercase = lowercase
        self.remove_punctuation = remove_punctuation
        self.standardize_spaces = standardize_spaces
        self.regex = regex or []
        self.tokenizer = self._get_tokenizer(tokenizer)
        self.cleaning_steps = self._configure_cleaning_steps()

    def _get_tokenizer(
        self, tokenizer: Union[str, Callable[[str], List[str]]]
    ) -> Callable[[str], List[str]]:
        """
        Get the tokenization function based on the specified tokenizer.

        Args:
            tokenizer: Either "basic" or a custom tokenization function.

        Returns:
            Callable[[str], List[str]]: The tokenization function.

        Raises:
            ValueError: If an unsupported tokenizer string is specified.
        """
        if callable(tokenizer):
            return tokenizer
        elif tokenizer == "basic":
            return lambda text: text.split()
        else:
            raise ValueError(
                f"Unsupported tokenizer: {tokenizer}. Use 'basic' or provide a custom tokenization function."
            )

    def _configure_cleaning_steps(self) -> List[Callable[[str], str]]:
        """
        Configure the text cleaning steps based on the preprocessor configuration.

        Returns:
            List[Callable[[str], str]]: List of text cleaning functions.
        """
        steps = []
        if self.lowercase:
            steps.append(lambda text: text.lower())

        regex_steps = []
        if self.regex:
            regex_steps.extend(self.regex)
        else:
            if self.remove_punctuation:
                regex_steps.append((r"[^\w\s]", ""))
            if self.standardize_spaces:
                regex_steps.append((r"\s+", " "))

        for pattern, repl in regex_steps:
            steps.append(self._create_regex_step(pattern, repl))

        if self.standardize_spaces:
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
        doc.preprocessed_text = preprocessed_text

        if self.tokenizer:
            tokens = self.tokenizer(preprocessed_text)
            doc.tokens = tokens

        return doc
