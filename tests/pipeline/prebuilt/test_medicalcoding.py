from unittest.mock import patch
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.pipeline.base import ModelConfig, ModelSource
from healthchain.pipeline.medicalcodingpipeline import MedicalCodingPipeline
from healthchain.io.containers import Document


def test_coding_pipeline(mock_spacy_nlp, test_document):
    """Test pure pipeline processing (Document → Document)"""
    with patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_spacy_nlp,
    ):
        pipeline = MedicalCodingPipeline()
        config = ModelConfig(
            source=ModelSource.SPACY,
            pipeline_object="en_core_sci_sm",
            path=None,
            kwargs={},
        )
        pipeline.configure_pipeline(config)

        # Process Document through pure pipeline
        result_doc = pipeline(test_document)

        # Assertions - pipeline should return processed Document
        assert isinstance(result_doc, Document)
        assert result_doc.data == "Test note"
        assert result_doc.fhir.problem_list[0].code.coding[0].display == "Hypertension"

        # Verify that the Model was called
        mock_spacy_nlp.assert_called_once_with(
            ModelConfig(
                source=ModelSource.SPACY,
                pipeline_object="en_core_sci_sm",
                task="ner",
                path=None,
                kwargs={},
            )
        )
        mock_spacy_nlp.return_value.assert_called_once()

        # Verify stages are set correctly
        assert len(pipeline._stages) == 2
        assert "ner+l" in pipeline._stages
        assert "problem-extraction" in pipeline._stages


def test_coding_pipeline_process_request(mock_spacy_nlp, mock_cda_adapter):
    """Test process_request method with adapter"""
    with patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_spacy_nlp,
    ), patch("healthchain.io.CdaAdapter", mock_cda_adapter):
        pipeline = MedicalCodingPipeline()
        config = ModelConfig(
            source=ModelSource.SPACY,
            pipeline_object="en_core_sci_sm",
            path=None,
            kwargs={},
        )
        pipeline.configure_pipeline(config)

        # Create a sample CdaRequest
        test_cda_request = CdaRequest(document="<xml>Sample CDA</xml>")

        # Process via convenience method
        cda_response = pipeline.process_request(test_cda_request)

        # Assertions
        assert isinstance(cda_response, CdaResponse)

        # Verify adapter was used correctly
        mock_cda_adapter.return_value.parse.assert_called_once_with(test_cda_request)
        mock_cda_adapter.return_value.format.assert_called_once()

        # Verify model was called
        mock_spacy_nlp.return_value.assert_called_once()


def test_full_coding_pipeline_integration(mock_spacy_nlp, test_cda_request):
    """Test integration with process_request method"""
    with patch(
        "healthchain.pipeline.mixins.ModelRoutingMixin.get_model_component",
        mock_spacy_nlp,
    ):
        pipeline = MedicalCodingPipeline.from_local_model(
            "./spacy/path/to/production/model", source="spacy"
        )

        # Use process_request for end-to-end processing
        cda_response = pipeline.process_request(test_cda_request)

        assert isinstance(cda_response, CdaResponse)

        assert "Aspirin" in cda_response.document
        assert "Hypertension" in cda_response.document
        # assert "Allergy to peanuts" in cda_response.document
