import pytest
from healthchain.io.containers import Document


@pytest.fixture
def sample_document():
    return Document(data="This is a sample text for testing.")


def test_document_initialization(sample_document):
    assert sample_document.data == "This is a sample text for testing."
    assert sample_document.text == "This is a sample text for testing."
    assert sample_document.nlp.get_tokens() == [
        "This",
        "is",
        "a",
        "sample",
        "text",
        "for",
        "testing.",
    ]
    assert sample_document.nlp.get_entities() == []
    assert sample_document.nlp.get_embeddings() is None


def test_document_word_count(sample_document):
    assert sample_document.word_count() == 7


def test_document_add_huggingface_output(sample_document):
    mock_output = {"label": "POSITIVE", "score": 0.9}

    sample_document.models.add_output("huggingface", "sentiment", mock_output)

    assert sample_document.models.get_output("huggingface", "sentiment") == mock_output


def test_document_add_langchain_output(sample_document):
    mock_output = "Summarized text"

    sample_document.models.add_output("langchain", "summarization", mock_output)

    assert (
        sample_document.models.get_output("langchain", "summarization") == mock_output
    )


def test_document_embeddings(sample_document):
    embeddings = [0.1, 0.2, 0.3]

    sample_document.nlp.set_embeddings(embeddings)

    assert sample_document.nlp.get_embeddings() == embeddings


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
    assert len(sample_document) == 34
