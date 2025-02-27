import pytest

from healthchain.pipeline.components import CdsCardCreator


@pytest.fixture
def test_lookup():
    return {
        "high blood pressure": "hypertension",
        "heart attack": "myocardial infarction",
    }


@pytest.fixture
def test_card_creator():
    return CdsCardCreator()


@pytest.fixture
def test_custom_template_creator():
    template = """
    {
        "summary": "Custom: {{ model_output }}",
        "indicator": "warning",
        "source": {{ default_source | tojson }},
        "detail": "{{ model_output }}"
    }
    """
    return CdsCardCreator(template=template)
