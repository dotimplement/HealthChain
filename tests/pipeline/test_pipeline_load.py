import pytest
from pathlib import Path
from healthchain.pipeline.base import ModelSource
from healthchain.io.containers import DataContainer


def test_load_huggingface_model(mock_basic_pipeline):
    pipeline = mock_basic_pipeline.load(
        "meta-llama/Llama-2-7b", task="text-generation", device="cuda", batch_size=32
    )

    assert pipeline._model_config.source == ModelSource.HUGGINGFACE
    assert pipeline._model_config.model_id == "meta-llama/Llama-2-7b"
    assert pipeline._model_config.path is None
    assert pipeline._model_config.config == {
        "task": "text-generation",
        "device": "cuda",
        "batch_size": 32,
    }


def test_load_spacy_model(mock_basic_pipeline):
    pipeline = mock_basic_pipeline.load(
        "en_core_sci_md", source="spacy", disable=["parser", "ner"]
    )

    assert pipeline._model_config.source == ModelSource.SPACY
    assert pipeline._model_config.model_id == "en_core_sci_md"
    assert pipeline._model_config.path is None
    assert pipeline._model_config.config == {"disable": ["parser", "ner"]}


def test_load_local_model(mock_basic_pipeline):
    pipeline = mock_basic_pipeline.load("./models/custom_spacy_model", source="spacy")

    assert pipeline._model_config.source == ModelSource.SPACY
    assert pipeline._model_config.model_id == "custom_spacy_model"
    assert isinstance(pipeline._model_config.path, Path)
    assert str(pipeline._model_config.path) == "models/custom_spacy_model"


def test_load_with_template(mock_basic_pipeline):
    template = """
    {
        "summary": "Test summary",
        "detail": "{{ model_output }}"
    }
    """

    pipeline = mock_basic_pipeline.load(
        "gpt-3.5-turbo", source="huggingface", template=template
    )

    assert pipeline._output_template == template
    assert pipeline._model_config.source == ModelSource.HUGGINGFACE
    assert pipeline._model_config.model_id == "gpt-3.5-turbo"


def test_load_callable_chain(mock_basic_pipeline, mock_chain):
    pipeline = mock_basic_pipeline.load(mock_chain, temperature=0.7, max_tokens=100)

    assert pipeline._model_config.source == ModelSource.LANGCHAIN
    assert pipeline._model_config.model_id == "langchain_chain"
    assert pipeline._model_config.config == {"temperature": 0.7, "max_tokens": 100}

    with pytest.raises(
        ValueError, match="LangChain models must be passed directly as chain objects"
    ):
        mock_basic_pipeline.load("langchain", source="langchain")


def test_load_invalid_source(mock_basic_pipeline):
    with pytest.raises(ValueError, match="Unsupported model source"):
        mock_basic_pipeline.load("model", source="invalid_source")


def test_load_with_simple_callable(mock_basic_pipeline):
    # Create a simple callable
    def simple_chain(input_text: str) -> str:
        return f"Processed: {input_text}"

    pipeline = mock_basic_pipeline.load(simple_chain, temperature=0.7)

    assert pipeline._model_config.source == ModelSource.LANGCHAIN
    assert pipeline._model_config.model_id == "langchain_chain"
    assert pipeline._model_config.config == {"temperature": 0.7}


def test_load_preserves_pipeline_functionality(mock_basic_pipeline):
    pipeline = mock_basic_pipeline.load("test-model")

    # Add a simple component
    @pipeline.add_node(name="test_component")
    def test_component(data: DataContainer):
        data.data = "processed"
        return data

    # Test that the pipeline still works
    result = pipeline("test")
    assert result.data == "processed"
