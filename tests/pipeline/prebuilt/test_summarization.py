from unittest.mock import patch
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.pipeline.base import ModelConfig, ModelSource
from healthchain.pipeline.summarizationpipeline import SummarizationPipeline


def test_summarization_pipeline(mock_cds_fhir_connector, mock_llm, test_cds_request):
    with patch(
        "healthchain.pipeline.summarizationpipeline.CdsFhirConnector",
        mock_cds_fhir_connector,
    ), patch(
        "healthchain.pipeline.summarizationpipeline.ModelRouter.get_component", mock_llm
    ):
        # This also doesn't do anything yet
        pipeline = SummarizationPipeline.load("llama3")

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
        mock_llm.assert_called_once_with(
            ModelConfig(
                source=ModelSource.HUGGINGFACE,
                model_id="llama3",
                path=None,
                config={"task": "summarization"},
            )
        )
        mock_llm.return_value.assert_called_once()

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


def test_full_summarization_pipeline_integration(mock_llm, test_cds_request):
    # Use mock LLM object for now
    with patch(
        "healthchain.pipeline.summarizationpipeline.ModelRouter.get_component", mock_llm
    ):
        pipeline = SummarizationPipeline.load("llama3")

        cds_response = pipeline(test_cds_request)
        print(cds_response)

        assert isinstance(cds_response, CDSResponse)
        assert len(cds_response.cards) == 1
        assert cds_response.cards[0].summary == "Summarized discharge information"
        assert "Patient John Doe" in cds_response.cards[0].detail
        assert "Encounter details" in cds_response.cards[0].detail
