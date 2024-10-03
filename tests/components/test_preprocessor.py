import pytest
from healthchain.pipeline.components.preprocessors import (
    TextPreProcessor,
    TextPreprocessorConfig,
)
from healthchain.io.containers import Document


def test_text_preprocessor_basic_config():
    basic_config = TextPreprocessorConfig(
        tokenizer="basic",
        lowercase=True,
        remove_punctuation=True,
        standardize_spaces=True,
    )
    basic_preprocessor = TextPreProcessor(basic_config)

    doc = Document("Hello, World!  This is a TEST.")
    processed_doc = basic_preprocessor(doc)

    assert processed_doc.preprocessed_text == "hello world this is a test"
    assert processed_doc.tokens == ["hello", "world", "this", "is", "a", "test"]


def test_text_preprocessor_custom_regex_config():
    custom_regex_config = TextPreprocessorConfig(
        tokenizer="basic",
        regex=[
            (r"\d+", "<NUM>"),  # Replace numbers with <NUM>
        ],
    )
    custom_regex_preprocessor = TextPreProcessor(custom_regex_config)

    doc = Document("There are 42 apples and 7 oranges!")
    processed_doc = custom_regex_preprocessor(doc)

    assert (
        processed_doc.preprocessed_text == "There are <NUM> apples and <NUM> oranges!"
    )
    assert processed_doc.tokens == [
        "There",
        "are",
        "<NUM>",
        "apples",
        "and",
        "<NUM>",
        "oranges!",
    ]


def test_text_preprocessor_default_config():
    config = TextPreprocessorConfig()  # Default config
    preprocessor = TextPreProcessor(config)

    doc = Document("Hello, World! This is a TEST with 42 numbers.")
    processed_doc = preprocessor(doc)

    assert (
        processed_doc.preprocessed_text
        == "Hello, World! This is a TEST with 42 numbers."
    )
    assert processed_doc.tokens == [
        "Hello,",
        "World!",
        "This",
        "is",
        "a",
        "TEST",
        "with",
        "42",
        "numbers.",
    ]


def test_text_preprocessor_invalid_tokenizer():
    with pytest.raises(ValueError, match="Unsupported tokenizer: invalid"):
        TextPreProcessor(TextPreprocessorConfig(tokenizer="invalid"))