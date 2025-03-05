from healthchain.io.containers.document import Document
from unittest.mock import patch, MagicMock


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


@patch("healthchain.io.containers.document.Span")
def test_update_problem_list_from_nlp(mock_span_class, test_empty_document):
    """Test updating problem list from NLP entities"""

    # Create mock spaCy entities
    mock_ent1 = MagicMock()
    mock_ent1.text = "Hypertension"
    mock_ent1._.cui = "38341003"

    mock_ent2 = MagicMock()
    mock_ent2.text = "Aspirin"
    mock_ent2._.cui = "123454"

    mock_ent3 = MagicMock()
    mock_ent3.text = "Allergy to peanuts"
    mock_ent3._.cui = "70618"

    # Create mock spaCy doc
    mock_spacy_doc = MagicMock()
    mock_spacy_doc.ents = [mock_ent1, mock_ent2, mock_ent3]

    # Add the spaCy doc to the test document
    test_empty_document.nlp.add_spacy_doc(mock_spacy_doc)

    # Update problem list from NLP entities
    test_empty_document.update_problem_list_from_nlp()

    # Verify problems were added correctly
    conditions = test_empty_document.fhir.problem_list
    assert len(conditions) == 3  # All entities are treated as problems by default

    # Check each problem was added with correct attributes
    expected_problems = [
        ("Hypertension", "38341003"),
        ("Aspirin", "123454"),
        ("Allergy to peanuts", "70618"),
    ]

    for i, (text, cui) in enumerate(expected_problems):
        assert conditions[i].code.coding[0].display == text
        assert conditions[i].code.coding[0].code == cui
        assert conditions[i].code.coding[0].system == "http://snomed.info/sct"
