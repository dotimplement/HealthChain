import pytest
from healthchain.pipeline.components.preprocessors import TextPreProcessor
from healthchain.io.containers import Document


def test_text_preprocessor_basic_config():
    basic_preprocessor = TextPreProcessor(
        tokenizer="basic",
        lowercase=True,
        remove_punctuation=True,
        standardize_spaces=True,
    )

    doc = Document("Hello, World!  This is a TEST.")
    processed_doc = basic_preprocessor(doc)

    assert processed_doc.preprocessed_text == "hello world this is a test"
    assert processed_doc.tokens == ["hello", "world", "this", "is", "a", "test"]


def test_text_preprocessor_callable_tokenizer():
    # Custom tokenizer that splits on vowels
    def custom_tokenizer(text):
        return [t for t in text.split() if t]

    preprocessor = TextPreProcessor(tokenizer=custom_tokenizer, lowercase=True)

    doc = Document("Hello World")
    processed_doc = preprocessor(doc)

    assert processed_doc.preprocessed_text == "hello world"
    assert processed_doc.tokens == ["hello", "world"]


def test_text_preprocessor_custom_regex_config():
    custom_regex_preprocessor = TextPreProcessor(
        tokenizer="basic",
        regex=[
            (r"\d+", "<NUM>"),  # Replace numbers with <NUM>
        ],
    )

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
    preprocessor = TextPreProcessor()  # Default config

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
        TextPreProcessor(tokenizer="invalid")
