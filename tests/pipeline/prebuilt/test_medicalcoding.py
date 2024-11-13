from unittest.mock import patch
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.pipeline.base import ModelConfig, ModelSource
from healthchain.pipeline.medicalcodingpipeline import MedicalCodingPipeline


def test_coding_pipeline(mock_cda_connector, mock_spacy_nlp):
    with patch(
        "healthchain.pipeline.medicalcodingpipeline.CdaConnector", mock_cda_connector
    ), patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_spacy_nlp,
    ):
        pipeline = MedicalCodingPipeline()
        config = ModelConfig(
            source=ModelSource.SPACY, model="en_core_sci_sm", path=None, kwargs={}
        )
        pipeline.configure_pipeline(config)

        # Create a sample CdaRequest
        test_cda_request = CdaRequest(document="<xml>Sample CDA</xml>")

        # Process the request through the pipeline
        cda_response = pipeline(test_cda_request)

        # Assertions
        assert isinstance(cda_response, CdaResponse)
        assert cda_response.document == "<xml>Updated CDA</xml>"

        # Verify that CdaConnector methods were called correctly
        mock_cda_connector.return_value.input.assert_called_once_with(test_cda_request)
        mock_cda_connector.return_value.output.assert_called_once()

        # Verify that the Model was called
        mock_spacy_nlp.assert_called_once_with(
            ModelConfig(
                source=ModelSource.SPACY,
                model="en_core_sci_sm",
                path=None,
                kwargs={"task": "ner"},
            )
        )
        mock_spacy_nlp.return_value.assert_called_once()

        # Verify the pipeline used the mocked input and output
        input_doc = mock_cda_connector.return_value.input.return_value
        assert input_doc.data == "Original note"
        assert (
            input_doc._hl7._ccd_data.concepts.problems[0].display_name == "Hypertension"
        )
        assert (
            input_doc._hl7._ccd_data.concepts.medications[0].display_name == "Aspirin"
        )
        assert (
            input_doc._hl7._ccd_data.concepts.allergies[0].display_name
            == "Allergy to peanuts"
        )

        # Verify stages are set correctly
        assert len(pipeline._stages) == 1
        assert "ner+l" in pipeline._stages


def test_full_coding_pipeline_integration(mock_spacy_nlp, test_cda_request):
    with patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_spacy_nlp,
    ):
        pipeline = MedicalCodingPipeline.load(
            "./spacy/path/to/production/model", source="spacy"
        )

        cda_response = pipeline(test_cda_request)

        assert isinstance(cda_response, CdaResponse)

        assert "Aspirin" in cda_response.document
        assert "Hypertension" in cda_response.document
        assert "Allergy to peanuts" in cda_response.document
