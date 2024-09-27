import pytest

from healthchain.pipeline.components.preprocessors import (
    TextPreprocessor,
    TextPreprocessorConfig,
)


@pytest.fixture
def basic_preprocessor():
    config = TextPreprocessorConfig(
        tokenizer="basic",
        lowercase=True,
        remove_punctuation=True,
        standardize_spaces=True,
    )
    return TextPreprocessor(config)


@pytest.fixture
def custom_regex_preprocessor():
    config = TextPreprocessorConfig(
        tokenizer="basic",
        regex=[
            (r"\d+", "<NUM>"),  # Replace numbers with <NUM>
        ],
    )
    return TextPreprocessor(config)


@pytest.fixture
def sample_lookup():
    return {
        "high blood pressure": "hypertension",
        "heart attack": "myocardial infarction",
    }
