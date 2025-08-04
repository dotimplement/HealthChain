import pytest
from unittest.mock import Mock, patch, MagicMock
from healthchain.io.containers import Document
from healthchain.io.containers.document import (
    FhirData,
    ModelOutputs,
)

from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.pipeline.base import BasePipeline, ModelConfig, ModelSource
from healthchain.models.responses.cdsresponse import CDSResponse, Card
from healthchain.pipeline.modelrouter import ModelRouter


# Basic object fixtures


@pytest.fixture
def cds_fhir_adapter():
    from healthchain.io import CdsFhirAdapter

    return CdsFhirAdapter(hook_name="patient-view")


@pytest.fixture
def router():
    return ModelRouter()


@pytest.fixture
def mock_basic_pipeline():
    class TestPipeline(BasePipeline):
        def configure_pipeline(self, model_config):
            self._model_config = model_config

    return TestPipeline()


@pytest.fixture
def mock_chain():
    chain = Mock()
    chain.invoke = Mock(return_value="Test response")
    chain.__call__ = Mock(return_value="Test response")
    return chain


# Config fixtures


@pytest.fixture
def spacy_config():
    return ModelConfig(
        source=ModelSource.SPACY,
        model_id="en_core_sci_md",
        pipeline_object=None,
        path=None,
        kwargs={"disable": ["parser"]},
    )


@pytest.fixture
def hf_config():
    return ModelConfig(
        source=ModelSource.HUGGINGFACE,
        model_id="bert-base",
        task="ner",
        pipeline_object=None,
        path=None,
        kwargs={},
    )


# CDS connector fixtures


@pytest.fixture
def mock_cds_card_creator():
    with patch("healthchain.pipeline.modelrouter.ModelRouter.get_component") as mock:
        llm_instance = mock.return_value
        document = Document(data="Summarized discharge information")
        document.cds.cards = [
            Card(
                summary="Summarized discharge information",
                detail="Patient John Doe was discharged. Encounter details...",
                indicator="info",
                source={"label": "Summarization LLM"},
            )
        ]
        llm_instance.return_value = document
        yield mock


@pytest.fixture
def mock_cds_fhir_adapter(test_condition):
    with patch("healthchain.io.CdsFhirAdapter") as mock:
        adapter_instance = mock.return_value

        # Mock the parse method
        fhir_data = FhirData()
        fhir_data.prefetch_resources = {"problem": test_condition}

        adapter_instance.parse.return_value = Document(
            data="Original FHIR data",
            _fhir=fhir_data,
        )

        # Mock the format method
        adapter_instance.format.return_value = CDSResponse(
            cards=[
                Card(
                    summary="Summarized discharge information",
                    detail="Patient John Doe was discharged. Encounter details...",
                    indicator="info",
                    source={"label": "Summarization LLM"},
                )
            ]
        )

        yield mock


# CDA adapter fixtures


@pytest.fixture
def mock_cda_adapter(test_document):
    with patch("healthchain.io.CdaAdapter") as mock:
        adapter_instance = mock.return_value

        # Mock the parse method
        adapter_instance.parse.return_value = test_document

        # Mock the format method
        adapter_instance.format.return_value = CdaResponse(
            document="<xml>Updated CDA</xml>"
        )

        yield mock


# Adapter fixtures


# NLP component fixtures


@pytest.fixture
def mock_spacy_nlp(test_document):
    with patch("healthchain.pipeline.components.integrations.SpacyNLP") as mock:
        # Create mock spaCy entities
        mock_ent = MagicMock()
        mock_ent.text = "Hypertension"
        mock_ent._.cui = "38341003"

        mock_ent2 = MagicMock()
        mock_ent2.text = "Aspirin"
        mock_ent2._.cui = "123454"

        mock_ent3 = MagicMock()
        mock_ent3.text = "Allergy to peanuts"
        mock_ent3._.cui = "70618"

        # Create mock spaCy doc
        mock_spacy_doc = MagicMock()
        mock_spacy_doc.ents = [mock_ent, mock_ent2, mock_ent3]

        test_document._nlp._spacy_doc = mock_spacy_doc

        # Setup the component instance
        component_instance = mock.return_value
        component_instance.return_value = test_document

        yield mock


@pytest.fixture
def mock_hf_transformer():
    with patch("healthchain.pipeline.components.integrations.HFTransformer") as mock:
        # Setup the component instance
        component_instance = mock.return_value
        component_instance.task = "sentiment-analysis"
        component_instance.return_value = Document(
            data="Original text",
            _models=ModelOutputs(
                _huggingface_results={
                    "sentiment-analysis": [{"label": "POSITIVE", "score": 0.9}],
                    "summarization": [
                        {"summary_text": "Generated response from Hugging Face"}
                    ],
                }
            ),
        )
        yield mock


@pytest.fixture
def mock_langchain_llm():
    with patch("healthchain.pipeline.components.integrations.LangChainLLM") as mock:
        # Setup the component instance
        component_instance = mock.return_value
        component_instance.return_value = Document(
            data="Original text",
            _models=ModelOutputs(
                _langchain_results={
                    "summarization": "Generated response from LangChain",
                    "structured_generation": {
                        "structured_output": "Generated response from LangChain"
                    },
                }
            ),
        )
        yield mock
