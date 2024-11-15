import pytest
from unittest.mock import Mock, patch

from healthchain.pipeline.base import ModelConfig, ModelSource


def test_router_initialization(router):
    """Test that router initializes with correct mapping of sources to init functions"""
    assert ModelSource.SPACY in router._init_functions
    assert ModelSource.HUGGINGFACE in router._init_functions
    assert callable(router._init_functions[ModelSource.SPACY])
    assert callable(router._init_functions[ModelSource.HUGGINGFACE])


def test_get_component_invalid_source(router):
    """Test that router raises error for invalid model source"""
    invalid_config = ModelConfig(source="invalid", pipeline_object="test")
    with pytest.raises(ValueError, match="Unsupported model source"):
        router.get_component(invalid_config)


@patch("healthchain.pipeline.components.integrations.SpacyNLP")
def test_get_component_spacy(mock_spacy, router, spacy_config):
    """Test initialization of SpaCy component"""
    mock_instance = Mock()
    mock_spacy.from_model_id.return_value = mock_instance

    component = router.get_component(spacy_config)

    mock_spacy.from_model_id.assert_called_once_with(
        model="en_core_sci_md", disable=["parser"]
    )
    assert component == mock_instance


@patch("healthchain.pipeline.components.integrations.SpacyNLP")
def test_get_component_spacy_local(mock_spacy, router):
    """Test initialization of SpaCy component with local model path"""
    mock_instance = Mock()
    mock_spacy.from_model_id.return_value = mock_instance

    local_spacy_config = ModelConfig(
        source=ModelSource.SPACY,
        model_id="custom_model",
        path="./models/spacy/custom",
        kwargs={},
    )

    component = router.get_component(local_spacy_config)

    mock_spacy.from_model_id.assert_called_once_with(model=str(local_spacy_config.path))
    assert component == mock_instance


@patch("healthchain.pipeline.components.integrations.HFTransformer")
def test_get_component_huggingface(mock_hf, router, hf_config):
    """Test initialization of Hugging Face component"""
    mock_instance = Mock()
    mock_hf.from_model_id.return_value = mock_instance

    component = router.get_component(hf_config)

    mock_hf.from_model_id.assert_called_once_with(task="ner", model="bert-base")
    assert component == mock_instance


@patch("healthchain.pipeline.components.integrations.HFTransformer")
def test_get_component_huggingface_local(mock_hf, router):
    """Test initialization of Hugging Face component with local model path"""
    config = ModelConfig(
        source=ModelSource.HUGGINGFACE,
        model_id="local-bert",
        task="ner",
        path="./models/hf/bert",
        kwargs={},
    )
    mock_instance = Mock()
    mock_hf.from_model_id.return_value = mock_instance

    component = router.get_component(config)

    mock_hf.from_model_id.assert_called_once_with(task="ner", model=str(config.path))
    assert component == mock_instance


def test_get_component_missing_dependencies(router, spacy_config):
    """Test handling of missing dependencies"""
    with patch(
        "healthchain.pipeline.components.integrations.SpacyNLP.from_model_id",
        side_effect=ImportError,
    ):
        with pytest.raises(ImportError):
            router.get_component(spacy_config)


def test_model_config_storage(router, spacy_config):
    """Test that router correctly stores model config for use in init functions"""
    with patch("healthchain.pipeline.components.integrations.SpacyNLP"):
        router.get_component(spacy_config)
        assert router.model_config == spacy_config
