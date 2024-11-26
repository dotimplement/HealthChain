import pytest
from healthchain.io.containers import Document
from healthchain.models.responses import Card, Action
from healthchain.models.data import CcdData
from healthchain.models.data.concept import (
    ProblemConcept,
    MedicationConcept,
    AllergyConcept,
)


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


def test_document_add_concepts(sample_document):
    problems = [ProblemConcept(display_name="Hypertension")]
    medications = [MedicationConcept(display_name="Aspirin")]
    allergies = [AllergyConcept(display_name="Penicillin")]

    sample_document.add_concepts(
        problems=problems, medications=medications, allergies=allergies
    )

    assert sample_document.concepts.problems == problems
    assert sample_document.concepts.medications == medications
    assert sample_document.concepts.allergies == allergies


def test_document_generate_ccd(sample_document):
    problems = [ProblemConcept(display_name="Hypertension")]
    sample_document.add_concepts(problems=problems)

    ccd_data = sample_document.generate_ccd()
    assert isinstance(ccd_data, CcdData)
    assert ccd_data.concepts.problems == problems


def test_document_add_cds_cards(sample_document):
    cards = [
        {
            "summary": "Test Card",
            "detail": "Test Detail",
            "indicator": "info",
            "source": {"label": "Test Source"},
        }
    ]
    sample_document.add_cds_cards(cards)

    assert isinstance(sample_document.cds.get_cards()[0], Card)
    assert sample_document.cds.get_cards()[0].summary == "Test Card"


def test_document_add_cds_actions(sample_document):
    actions = [
        {"type": "create", "description": "Test Action", "resource": {"test": "test"}}
    ]
    sample_document.add_cds_actions(actions)

    assert isinstance(sample_document.cds.get_actions()[0], Action)
    assert sample_document.cds.get_actions()[0].description == "Test Action"


def test_document_add_huggingface_output(sample_document):
    mock_output = [
        {"label": "POSITIVE", "score": 0.9, "generated_text": "Generated response"}
    ]

    sample_document.models.add_output("huggingface", "sentiment", mock_output)

    assert sample_document.models.get_output("huggingface", "sentiment") == mock_output
    assert sample_document.models.get_generated_text("huggingface", "sentiment") == [
        "Generated response"
    ]

    mock_output_chat = [
        {
            "generated_text": [
                {
                    "role": "user",
                    "content": "What is the capital of France? Answer in one word.",
                },
                {"role": "assistant", "content": "Paris"},
            ]
        }
    ]
    sample_document.models.add_output("huggingface", "chat", mock_output_chat)
    assert sample_document.models.get_output("huggingface", "chat") == mock_output_chat
    assert sample_document.models.get_generated_text("huggingface", "chat") == [
        "Paris",
    ]


def test_document_add_langchain_output(sample_document):
    mock_output = "Summarized text"
    sample_document.models.add_output("langchain", "summarization", mock_output)

    assert (
        sample_document.models.get_output("langchain", "summarization") == mock_output
    )
    assert sample_document.models.get_generated_text("langchain", "summarization") == [
        mock_output
    ]

    mock_output_json = {"test": "test"}
    sample_document.models.add_output("langchain", "json", mock_output_json)
    assert sample_document.models.get_generated_text("langchain", "json") == [
        '{"test": "test"}'
    ]


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


def test_document_word_count(sample_document):
    assert sample_document.word_count() == 7
