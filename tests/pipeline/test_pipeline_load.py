import pytest

from pathlib import Path
from healthchain.pipeline.base import ModelSource


def test_from_model_id_huggingface(mock_basic_pipeline):
    pipeline = mock_basic_pipeline.from_model_id(
        "meta-llama/Llama-2-7b", task="text-generation", device="cuda", batch_size=32
    )

    assert pipeline._model_config.source == ModelSource.HUGGINGFACE
    assert pipeline._model_config.model_id == "meta-llama/Llama-2-7b"
    assert pipeline._model_config.task == "text-generation"
    assert pipeline._model_config.path is None
    assert pipeline._model_config.pipeline_object is None
    assert pipeline._model_config.kwargs == {
        "device": "cuda",
        "batch_size": 32,
    }


def test_load_hf_pipeline(mock_basic_pipeline):
    def simple_callable(input_text: str) -> str:
        return f"Processed: {input_text}"

    pipeline = mock_basic_pipeline.load(
        simple_callable, source="huggingface", temperature=0.7
    )

    assert pipeline._model_config.source == ModelSource.HUGGINGFACE
    assert pipeline._model_config.pipeline_object == simple_callable
    assert pipeline._model_config.kwargs == {"temperature": 0.7}
    assert pipeline._model_config.model_id is None
    assert pipeline._model_config.path is None


def test_from_model_id_spacy(mock_basic_pipeline):
    pipeline = mock_basic_pipeline.from_model_id(
        "en_core_sci_md", source="spacy", disable=["parser", "ner"]
    )

    assert pipeline._model_config.source == ModelSource.SPACY
    assert pipeline._model_config.model_id == "en_core_sci_md"
    assert pipeline._model_config.path is None
    assert pipeline._model_config.pipeline_object is None
    assert pipeline._model_config.kwargs == {"disable": ["parser", "ner"]}


def test_from_local_model_spacy(mock_basic_pipeline):
    pipeline = mock_basic_pipeline.from_local_model(
        "./models/custom_spacy_model", source="spacy"
    )

    assert pipeline._model_config.source == ModelSource.SPACY
    assert pipeline._model_config.model_id == "custom_spacy_model"
    assert isinstance(pipeline._model_config.path, Path)
    assert str(pipeline._model_config.path) == "models/custom_spacy_model"
    assert pipeline._model_config.pipeline_object is None


def test_load_langchain(mock_basic_pipeline, mock_chain):
    pipeline = mock_basic_pipeline.load(
        mock_chain, source="langchain", temperature=0.7, max_tokens=100
    )

    assert pipeline._model_config.source == ModelSource.LANGCHAIN
    assert pipeline._model_config.pipeline_object == mock_chain
    assert pipeline._model_config.kwargs == {"temperature": 0.7, "max_tokens": 100}
    assert pipeline._model_config.model_id is None
    assert pipeline._model_config.path is None

    with pytest.raises(ValueError, match="Pipeline must be a callable object"):
        mock_basic_pipeline.load("langchain", source="langchain")


def test_from_model_id_invalid_source(mock_basic_pipeline):
    with pytest.raises(ValueError, match="not a valid ModelSource"):
        mock_basic_pipeline.from_model_id("model", source="invalid_source")


def test_load_with_template(mock_basic_pipeline):
    template = """
    {
        "summary": "Test summary",
        "detail": "{{ model_output }}"
    }
    """

    pipeline = mock_basic_pipeline.from_model_id(
        "gpt-3.5-turbo", source="huggingface", template=template
    )

    assert pipeline._output_template == template
    assert pipeline._model_config.source == ModelSource.HUGGINGFACE
    assert pipeline._model_config.model_id == "gpt-3.5-turbo"
    assert pipeline._model_config.pipeline_object is None


def test_load_with_template_path(mock_basic_pipeline, tmp_path):
    template_file = tmp_path / "test_template.json"
    template_content = """
    {
        "summary": "Test summary",
        "detail": "{{ model_output }}"
    }
    """
    template_file.write_text(template_content)

    pipeline = mock_basic_pipeline.from_model_id(
        "gpt-3.5-turbo", source="huggingface", template_path=template_file
    )

    assert pipeline._output_template_path == template_file
    assert pipeline._model_config.source == ModelSource.HUGGINGFACE
    assert pipeline._model_config.model_id == "gpt-3.5-turbo"
    assert pipeline._model_config.pipeline_object is None
