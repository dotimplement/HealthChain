from unittest.mock import patch
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.pipeline.base import ModelConfig, ModelSource
from healthchain.pipeline.summarizationpipeline import SummarizationPipeline


def test_summarization_pipeline(
    mock_cds_fhir_connector,
    mock_hf_transformer,
    mock_cds_card_creator,
    test_cds_request,
):
    with patch(
        "healthchain.pipeline.summarizationpipeline.CdsFhirConnector",
        mock_cds_fhir_connector,
    ), patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_hf_transformer,
    ), patch(
        "healthchain.pipeline.summarizationpipeline.CdsCardCreator",
        mock_cds_card_creator,
    ):
        pipeline = SummarizationPipeline()
        config = ModelConfig(
            source=ModelSource.HUGGINGFACE, model_id="llama3", path=None, config={}
        )
        pipeline.configure_pipeline(config)

        # Process the request through the pipeline
        cds_response = pipeline(test_cds_request)

        # Assertions
        assert isinstance(cds_response, CDSResponse)
        assert len(cds_response.cards) == 1
        assert cds_response.cards[0].summary == "Summarized discharge information"

        # Verify that CdsFhirConnector methods were called correctly
        mock_cds_fhir_connector.return_value.input.assert_called_once_with(
            test_cds_request
        )
        mock_cds_fhir_connector.return_value.output.assert_called_once()

        # Verify that the LLM was called
        mock_hf_transformer.assert_called_once_with(
            ModelConfig(
                source=ModelSource.HUGGINGFACE,
                model_id="llama3",
                path=None,
                config={"task": "summarization"},
            )
        )
        mock_hf_transformer.return_value.assert_called_once()

        mock_cds_card_creator.assert_called_once_with(
            source=ModelSource.HUGGINGFACE.value,
            task="summarization",
            template=pipeline._output_template,
        )

        # Verify the pipeline used the mocked input and output
        input_data = mock_cds_fhir_connector.return_value.input.return_value
        assert input_data.hl7._fhir_data.context == {
            "patientId": "123",
            "encounterId": "456",
        }
        assert input_data.hl7._fhir_data.model_dump_prefetch() == {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "123",
                        "name": [{"family": "Doe", "given": ["John"]}],
                        "gender": "male",
                        "birthDate": "1970-01-01",
                    }
                },
            ],
        }

        # Verify stages are set correctly
        assert len(pipeline._stages) == 2
        assert "summarization" in pipeline._stages
        assert "card-creation" in pipeline._stages


def test_full_summarization_pipeline_integration(mock_hf_transformer, test_cds_request):
    # Use mock LLM object for now
    with patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_hf_transformer,
    ):
        template = """
    {
        "summary": "This is a test summary",
        "indicator": "warning",
        "source": {{ default_source | tojson }},
        "detail": "{{ model_output }}"
    }
    """
        pipeline = SummarizationPipeline.load(
            "llama3", source="huggingface", template=template
        )

        cds_response = pipeline(test_cds_request)

        assert isinstance(cds_response, CDSResponse)
        assert len(cds_response.cards) == 1

        assert cds_response.cards[0].summary == "This is a test summary"
        assert cds_response.cards[0].indicator == "warning"
        assert cds_response.cards[0].detail == "Generated response from Hugging Face"
