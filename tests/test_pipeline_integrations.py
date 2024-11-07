import pytest
import importlib.util
from unittest.mock import Mock, patch, MagicMock
from healthchain.io.containers import Document
from healthchain.pipeline.components.integrations import (
    SpacyNLP,
    HFTransformer,
    LangChainLLM,
)

transformers_installed = importlib.util.find_spec("transformers") is not None


@pytest.fixture
def sample_document():
    return Document(data="This is a sample text for testing.")


@pytest.mark.parametrize(
    "component_class,mock_module,kwargs,expected_kwargs",
    [
        (
            SpacyNLP,
            "spacy.load",
            {"disable": ["ner", "parser"]},
            {"disable": ["ner", "parser"]},
        ),
        pytest.param(
            HFTransformer,
            "transformers.pipeline",
            {"device": "cuda", "batch_size": 32},
            {
                "task": "dummy_task",
                "model": "dummy_model",
                "device": "cuda",
                "batch_size": 32,
            },
            marks=pytest.mark.skipif(
                not transformers_installed, reason="transformers package not installed"
            ),
        ),
    ],
)
def test_component_initialization(
    component_class, mock_module, kwargs, expected_kwargs
):
    with patch(mock_module) as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        if component_class == SpacyNLP:
            component = component_class("dummy_path", **kwargs)
        else:
            component = component_class("dummy_task", "dummy_model", **kwargs)

        mock.assert_called_once_with("dummy_path", **expected_kwargs)
        assert hasattr(component, "nlp")
        assert component.nlp == mock_instance


def test_spacy_component(sample_document):
    with patch("spacy.load") as mock_load:
        mock_instance = MagicMock(items=[])
        mock_instance.__iter__.return_value = []
        mock_load.return_value = mock_instance

        # Test with and without kwargs
        test_cases = [
            ({"disable": ["ner", "parser"]}, "with kwargs"),
            ({}, "without kwargs"),
        ]

        for kwargs, case in test_cases:
            component = SpacyNLP("en_core_web_sm", **kwargs)
            result = component(sample_document)

            # Verify kwargs were passed correctly
            expected_args = {"disable": ["ner", "parser"]} if kwargs else {}
            mock_load.assert_called_with("en_core_web_sm", **expected_args)

            assert result.nlp.get_spacy_doc(), f"SpacyNLP failed {case}"
            mock_load.reset_mock()


@pytest.mark.skipif(
    not transformers_installed, reason="transformers package not installed"
)
def test_huggingface_component(sample_document):
    with patch("transformers.pipeline") as mock_pipeline:
        mock_instance = Mock()
        mock_pipeline.return_value = mock_instance

        # Test with and without kwargs
        test_cases = [
            (
                {
                    "device": "cuda",
                    "batch_size": 32,
                    "max_length": 512,
                    "truncation": True,
                },
                "with kwargs",
            ),
            ({}, "without kwargs"),
        ]

        for kwargs, case in test_cases:
            component = HFTransformer(
                "sentiment-analysis",
                "distilbert-base-uncased-finetuned-sst-2-english",
                **kwargs,
            )
            result = component(sample_document)

            # Verify kwargs were passed correctly
            expected_kwargs = {
                "task": "sentiment-analysis",
                "model": "distilbert-base-uncased-finetuned-sst-2-english",
                **kwargs,
            }
            mock_pipeline.assert_called_once_with(**expected_kwargs)

            assert result.models.get_output(
                "huggingface", "sentiment-analysis"
            ), f"HFTransformer failed {case}"
            mock_pipeline.reset_mock()


def test_langchain_component(sample_document):
    mock_chain = Mock()
    mock_chain.invoke.return_value = "mocked chain output"

    # Test with and without kwargs
    test_cases = [
        (
            {"temperature": 0.7, "max_tokens": 100, "stop_sequences": ["END"]},
            "with kwargs",
        ),
        ({}, "without kwargs"),
    ]

    for kwargs, case in test_cases:
        component = LangChainLLM(mock_chain, **kwargs)
        result = component(sample_document)

        # Verify kwargs were passed correctly
        mock_chain.invoke.assert_called_once_with(sample_document.data, **kwargs)
        assert (
            result.models.get_output("langchain", "chain_output")
            == "mocked chain output"
        ), f"LangChainLLM failed {case}"
        mock_chain.invoke.reset_mock()


# Test error handling
@pytest.mark.parametrize(
    "component_class,args,kwargs,expected_error,expected_message",
    [
        (
            SpacyNLP,
            ["en_core_web_sm"],
            {"invalid_kwarg": "value"},
            TypeError,
            "Invalid kwargs for spacy.load",
        ),
        pytest.param(
            HFTransformer,
            ["sentiment-analysis", "model"],
            {"invalid_kwarg": "value"},
            TypeError,
            "Invalid kwargs for transformers.pipeline",
            marks=pytest.mark.skipif(
                not transformers_installed, reason="transformers package not installed"
            ),
        ),
        (
            LangChainLLM,
            [Mock()],  # Mock chain
            {"invalid_kwarg": "value"},
            TypeError,
            "Invalid kwargs for chain.invoke",
        ),
    ],
)
def test_component_invalid_kwargs(
    component_class, args, kwargs, expected_error, expected_message
):
    if component_class == SpacyNLP:
        with patch("spacy.load") as mock_spacy:
            mock_spacy.side_effect = TypeError(
                "got an unexpected keyword argument 'invalid_kwarg'"
            )
            with pytest.raises(expected_error) as exc_info:
                component_class(*args, **kwargs)

    elif component_class == HFTransformer:
        with patch("transformers.pipeline") as mock_transformers:
            mock_transformers.side_effect = TypeError(
                "got an unexpected keyword argument 'invalid_kwarg'"
            )
            with pytest.raises(expected_error) as exc_info:
                component_class(*args, **kwargs)

    else:  # LangChainLLM
        mock_chain = args[0]
        mock_chain.invoke.side_effect = TypeError(
            "got an unexpected keyword argument 'invalid_kwarg'"
        )
        with pytest.raises(expected_error) as exc_info:
            component = component_class(*args, **kwargs)
            component(Document("test"))

    assert expected_message in str(exc_info.value)
