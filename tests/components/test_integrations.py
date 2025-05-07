import pytest
import importlib.util
from unittest.mock import Mock, patch, MagicMock
from healthchain.io.containers import Document
from healthchain.pipeline.components.integrations import (
    SpacyNLP,
    HFTransformer,
    LangChainLLM,
    requires_package,
)

transformers_installed = importlib.util.find_spec("transformers") is not None
langchain_installed = importlib.util.find_spec("langchain_core") is not None


def test_spacy_component(test_empty_document):
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
            component = SpacyNLP.from_model_id("en_core_web_sm", **kwargs)
            result = component(test_empty_document)

            # Verify kwargs were passed correctly
            expected_args = {"disable": ["ner", "parser"]} if kwargs else {}
            mock_load.assert_called_with("en_core_web_sm", **expected_args)

            assert result.nlp.get_spacy_doc(), f"SpacyNLP failed {case}"
            mock_load.reset_mock()


@pytest.mark.skipif(
    not transformers_installed, reason="transformers package not installed"
)
def test_huggingface_component(test_empty_document):
    from transformers.pipelines.base import Pipeline

    with patch("transformers.pipeline", autospec=True) as mock_pipeline:
        # Create a mock that inherits from Pipeline
        mock_instance = Mock(spec=Pipeline)
        mock_instance.task = "sentiment-analysis"
        mock_instance.__class__ = Pipeline
        mock_pipeline.return_value = mock_instance

        kwargs = {
            "device": "mps",
            "batch_size": 32,
            "max_length": 512,
            "truncation": True,
        }

        component = HFTransformer.from_model_id(
            model="distilbert-base-uncased-finetuned-sst-2-english",
            task="sentiment-analysis",
            **kwargs,
        )
        result = component(test_empty_document)

        mock_pipeline.assert_called_once_with(
            task="sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            **kwargs,
        )

        assert result.models.get_output(
            "huggingface", "sentiment-analysis"
        ), "HFTransformer failed with kwargs"
        mock_pipeline.reset_mock()


@pytest.mark.skipif(
    not langchain_installed, reason="langchain-core package not installed"
)
def test_langchain_component(test_empty_document):
    from langchain_core.runnables import Runnable

    mock_chain = Mock(spec=Runnable)
    mock_chain.__class__ = Runnable  # Mock isinstance check
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
        component = LangChainLLM(chain=mock_chain, task="dummy_task", **kwargs)
        result = component(test_empty_document)

        # Verify kwargs were passed correctly
        mock_chain.invoke.assert_called_once_with(test_empty_document.data, **kwargs)
        assert (
            result.models.get_output("langchain", "dummy_task") == "mocked chain output"
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
            ["distilbert-base-uncased-finetuned-sst-2-english", "sentiment-analysis"],
            {"invalid_kwarg": "value"},
            TypeError,
            "Invalid kwargs for transformers.pipeline",
            marks=pytest.mark.skipif(
                not transformers_installed, reason="transformers package not installed"
            ),
        ),
        pytest.param(
            LangChainLLM,
            [Mock(), "dummy_task"],  # Mock chain
            {"invalid_kwarg": "value"},
            TypeError,
            "Invalid kwargs for chain.invoke",
            marks=pytest.mark.skipif(
                not langchain_installed, reason="langchain-core package not installed"
            ),
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
                component_class.from_model_id(*args, **kwargs)

    elif component_class == HFTransformer:
        from transformers.pipelines.base import Pipeline

        with patch("transformers.pipeline", autospec=True) as mock_transformers:
            # Set up the mock to raise the TypeError
            mock_transformers.side_effect = TypeError(
                "got an unexpected keyword argument 'invalid_kwarg'"
            )

            # Mock the Pipeline type check that happens in initialization
            mock_instance = Mock(spec=Pipeline)
            mock_instance.task = "sentiment-analysis"
            mock_instance.__class__ = Pipeline
            mock_transformers.return_value = mock_instance

            with pytest.raises(expected_error) as exc_info:
                component_class.from_model_id(model=args[0], task=args[1], **kwargs)

    else:  # LangChainLLM
        from langchain_core.runnables import Runnable

        mock_chain = args[0]
        mock_chain.__class__ = Runnable  # Mock isinstance check
        mock_chain.invoke.side_effect = TypeError(
            "got an unexpected keyword argument 'invalid_kwarg'"
        )
        with pytest.raises(expected_error) as exc_info:
            component = LangChainLLM(chain=mock_chain, task=args[1], **kwargs)
            component(Document("test"))

    assert expected_message in str(exc_info.value)


def test_requires_package_decorator():
    """Test the requires_package decorator handles missing packages correctly"""

    @requires_package("fake-package", "nonexistent.module")
    def dummy_function():
        return True

    with pytest.raises(ImportError) as exc_info:
        dummy_function()
    assert "This feature requires fake-package" in str(exc_info.value)
    assert "pip install fake-package" in str(exc_info.value)


@pytest.mark.skipif(
    not transformers_installed, reason="transformers package not installed"
)
def test_huggingface_pipeline_errors():
    """Test HFTransformer handles pipeline errors correctly"""

    with patch("transformers.pipeline") as mock_pipeline:
        # Test general pipeline initialization error
        mock_pipeline.side_effect = ValueError("Invalid model configuration")
        with pytest.raises(ValueError) as exc_info:
            HFTransformer.from_model_id(model="invalid-model", task="invalid-task")
        assert "Error initializing transformer pipeline" in str(exc_info.value)


@pytest.mark.skipif(
    not langchain_installed, reason="langchain-core package not installed"
)
def test_component_type_validation():
    """Test that components validate input types correctly"""

    # Test HFTransformer with invalid pipeline type
    if transformers_installed:
        with pytest.raises(TypeError) as exc_info:
            HFTransformer(pipeline=Mock())  # Not a Pipeline instance
        assert "Expected HuggingFace Pipeline object" in str(exc_info.value)

    # Test LangChainLLM with invalid chain type
    with pytest.raises(TypeError) as exc_info:
        LangChainLLM(chain=Mock(), task="test")  # Not a Runnable instance
    assert "Expected LangChain Runnable object" in str(exc_info.value)
