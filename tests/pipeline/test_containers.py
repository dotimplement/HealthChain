import pytest
from healthchain.io.containers import Document


@pytest.fixture
def sample_document():
    return Document(data="This is a sample text for testing.")


def test_document_initialization(sample_document):
    assert sample_document.data == "This is a sample text for testing."
    assert sample_document.text == "This is a sample text for testing."
    assert sample_document.tokens == [
        "This",
        "is",
        "a",
        "sample",
        "text",
        "for",
        "testing.",
    ]
    assert sample_document.entities == []
    assert sample_document.embeddings is None


def test_document_word_count(sample_document):
    assert sample_document.word_count() == 7


def test_document_char_count(sample_document):
    with pytest.raises(AttributeError):
        sample_document.char_count()  # Should raise error as spacy_doc is not set


def test_document_add_huggingface_output(sample_document):
    mock_output = {"label": "POSITIVE", "score": 0.9}

    sample_document.add_huggingface_output("sentiment", mock_output)

    assert sample_document.get_huggingface_output("sentiment") == mock_output


def test_document_add_langchain_output(sample_document):
    mock_output = "Summarized text"

    sample_document.add_langchain_output("summarization", mock_output)

    assert sample_document.get_langchain_output("summarization") == mock_output


def test_document_embeddings(sample_document):
    embeddings = [0.1, 0.2, 0.3]

    sample_document.set_embeddings(embeddings)

    assert sample_document.get_embeddings() == embeddings


def test_document_iteration(sample_document):
    assert list(sample_document) == [
        "This",
        "is",
        "a",
        "sample",
        "text",
        "for",
        "testing.",
    ]


def test_document_length(sample_document):
    assert len(sample_document) == 7
