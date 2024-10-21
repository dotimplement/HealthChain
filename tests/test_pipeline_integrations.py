import pytest
from unittest.mock import Mock, patch
from healthchain.io.containers import Document
from healthchain.pipeline.components.integrations import (
    SpacyComponent,
    HuggingFaceComponent,
    LangChainComponent,
)


@pytest.fixture
def sample_document():
    return Document(data="This is a sample text for testing.")


@pytest.mark.parametrize(
    "component_class,mock_module,mock_method",
    [
        (SpacyComponent, "spacy.load", "load"),
        (HuggingFaceComponent, "transformers.pipeline", "pipeline"),
    ],
)
def test_component_initialization(component_class, mock_module, mock_method):
    with patch(mock_module) as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        if component_class == SpacyComponent:
            component = component_class("dummy_path")
        else:
            component = component_class("dummy_task", "dummy_model")
        mock.assert_called_once()
        assert hasattr(component, "nlp")
        assert component.nlp == mock_instance


def test_spacy_component(sample_document):
    with patch("spacy.load"):
        component = SpacyComponent("en_core_web_sm")
        result = component(sample_document)
        assert result.spacy_doc


def test_huggingface_component(sample_document):
    with patch("transformers.pipeline"):
        component = HuggingFaceComponent(
            "sentiment-analysis", "distilbert-base-uncased-finetuned-sst-2-english"
        )
        result = component(sample_document)

        assert result.get_huggingface_output("sentiment-analysis")


def test_langchain_component(sample_document):
    mock_chain = Mock()
    mock_chain.invoke.return_value = "mocked chain output"

    component = LangChainComponent(mock_chain)
    result = component(sample_document)

    mock_chain.invoke.assert_called_once_with(sample_document.data)
    assert result.get_langchain_output("chain_output") == "mocked chain output"
