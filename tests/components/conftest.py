import pytest


@pytest.fixture
def sample_lookup():
    return {
        "high blood pressure": "hypertension",
        "heart attack": "myocardial infarction",
    }
