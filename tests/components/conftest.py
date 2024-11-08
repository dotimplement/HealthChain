import pytest
from healthchain.io.containers.document import Document
from tests.pipeline.conftest import mock_spacy_nlp  # noqa: F401


@pytest.fixture
def sample_lookup():
    return {
        "high blood pressure": "hypertension",
        "heart attack": "myocardial infarction",
    }


@pytest.fixture
def sample_document():
    return Document(data="This is a sample text for testing.")
