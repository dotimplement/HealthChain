from unittest.mock import patch
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.pipeline.base import ModelConfig, ModelSource
from healthchain.pipeline.summarizationpipeline import SummarizationPipeline
from healthchain.io.containers import Document


def test_summarization_pipeline(
    mock_hf_transformer,
    mock_cds_card_creator,
    test_document,
):
    """Test pure pipeline processing (Document → Document)"""
    with patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_hf_transformer,
    ), patch(
        "healthchain.pipeline.summarizationpipeline.CdsCardCreator",
        mock_cds_card_creator,
    ):
        pipeline = SummarizationPipeline()
        config = ModelConfig(
            source=ModelSource.HUGGINGFACE,
            pipeline_object="llama3",
            task="summarization",
            path=None,
            kwargs={},
        )
        pipeline.configure_pipeline(config)

        # Process Document through pure pipeline
        result_doc = pipeline(test_document)

        # Assertions - pipeline should return processed Document
        assert isinstance(result_doc, Document)

        # Verify that the LLM was called
        mock_hf_transformer.assert_called_once_with(
            ModelConfig(
                source=ModelSource.HUGGINGFACE,
                task="summarization",
                pipeline_object="llama3",
                path=None,
                kwargs={},
            )
        )
        mock_hf_transformer.return_value.assert_called_once()

        mock_cds_card_creator.assert_called_once_with(
            source=ModelSource.HUGGINGFACE.value,
            task="summarization",
            template=pipeline._output_template,
            template_path=pipeline._output_template_path,
            delimiter="\n",
        )

        # Verify stages are set correctly
        assert len(pipeline._stages) == 2
        assert "summarization" in pipeline._stages
        assert "card-creation" in pipeline._stages


def test_summarization_pipeline_process_request(
    mock_hf_transformer,
    mock_cds_card_creator,
    mock_cds_fhir_adapter,
    test_cds_request,
):
    """Test process_request method with adapter"""
    with patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_hf_transformer,
    ), patch(
        "healthchain.pipeline.summarizationpipeline.CdsCardCreator",
        mock_cds_card_creator,
    ), patch(
        "healthchain.io.CdsFhirAdapter",
        mock_cds_fhir_adapter,
    ):
        pipeline = SummarizationPipeline()
        config = ModelConfig(
            source=ModelSource.HUGGINGFACE,
            pipeline_object="llama3",
            task="summarization",
            path=None,
            kwargs={},
        )
        pipeline.configure_pipeline(config)

        # Process via convenience method
        cds_response = pipeline.process_request(test_cds_request)

        # Assertions
        assert isinstance(cds_response, CDSResponse)

        # Verify adapter was used correctly
        mock_cds_fhir_adapter.return_value.parse.assert_called_once_with(
            test_cds_request
        )
        mock_cds_fhir_adapter.return_value.format.assert_called_once()

        # Verify model was called
        mock_hf_transformer.return_value.assert_called_once()


def test_full_summarization_pipeline_integration(
    mock_hf_transformer, test_cds_request, tmp_path
):
    """Test integration with process_request method"""
    # Use mock LLM object for now
    with patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_hf_transformer,
    ):
        # Create a temporary template file
        template_file = tmp_path / "card_template.json"
        template_content = """
        {
            "summary": "This is a test summary",
            "indicator": "warning",
            "source": {{ default_source | tojson }},
            "detail": "{{ model_output }}"
        }
        """
        template_file.write_text(template_content)

        pipeline = SummarizationPipeline.from_model_id(
            "llama3", source="huggingface", template_path=template_file
        )

        # Use process_request for end-to-end processing
        cds_response = pipeline.process_request(test_cds_request)

        assert isinstance(cds_response, CDSResponse)
        assert len(cds_response.cards) == 1

        assert cds_response.cards[0].summary == "This is a test summary"
        assert cds_response.cards[0].indicator == "warning"
        assert cds_response.cards[0].detail == "Generated response from Hugging Face"
