from healthchain.io.containers.document import Document


def test_document_initialization(sample_document):
    """Test basic Document initialization and properties."""
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


def test_document_properties(sample_document):
    """Test Document property access."""
    # Test property access
    assert hasattr(sample_document, "nlp")
    assert hasattr(sample_document, "fhir")
    assert hasattr(sample_document, "cds")
    assert hasattr(sample_document, "models")


def test_document_word_count(sample_document):
    """Test word count functionality."""
    assert sample_document.word_count() == 7


def test_document_iteration(sample_document):
    """Test document iteration over tokens."""
    tokens = list(sample_document)
    assert tokens == [
        "This",
        "is",
        "a",
        "sample",
        "text",
        "for",
        "testing.",
    ]


def test_document_length(sample_document):
    """Test document length."""
    assert len(sample_document) == 34  # Length of the text string


def test_document_post_init(sample_document):
    """Test post-initialization behavior."""
    # Test that text is set from data
    assert sample_document.text == sample_document.data
    # Test that basic tokenization is performed
    assert len(sample_document.nlp._tokens) > 0


def test_empty_document():
    """Test Document initialization with empty text."""
    doc = Document("")
    assert doc.text == ""
    assert doc.nlp._tokens == []
    assert doc.word_count() == 0
