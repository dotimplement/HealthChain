import pytest
from healthchain.io.containers.document import Document
from healthchain.pipeline.components import CdsCardCreator
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


@pytest.fixture
def basic_creator():
    return CdsCardCreator()


@pytest.fixture
def custom_template_creator():
    template = """
    {
        "summary": "Custom: {{ model_output }}",
        "indicator": "warning",
        "source": {{ default_source | tojson }},
        "detail": "{{ model_output }}"
    }
    """
    return CdsCardCreator(template=template)
