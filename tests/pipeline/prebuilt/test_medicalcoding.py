from unittest.mock import patch
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.pipeline.medicalcodingpipeline import MedicalCodingPipeline


def test_coding_pipeline(mock_cda_connector, mock_model):
    with patch(
        "healthchain.pipeline.medicalcodingpipeline.CdaConnector", mock_cda_connector
    ), patch(
        "healthchain.pipeline.medicalcodingpipeline.ModelRouter.get_integration",
        mock_model,
    ):
        pipeline = MedicalCodingPipeline.load("./path/to/model")

        # Create a sample CdaRequest
        cda_request = CdaRequest(document="<xml>Sample CDA</xml>")

        # Process the request through the pipeline
        cda_response = pipeline(cda_request)

        # Assertions
        assert isinstance(cda_response, CdaResponse)
        assert cda_response.document == "<xml>Updated CDA</xml>"

        # Verify that CdaConnector methods were called correctly
        mock_cda_connector.return_value.input.assert_called_once_with(cda_request)
        mock_cda_connector.return_value.output.assert_called_once()

        # Verify that the Model was called
        mock_model.assert_called_once()
        mock_model.return_value.assert_called_once()

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


def test_full_coding_pipeline_integration(mock_model, test_cda_request):
    # Use mock model object for now
    with patch(
        "healthchain.pipeline.medicalcodingpipeline.ModelRouter.get_integration",
        mock_model,
    ):
        # this load method doesn't do anything yet
        pipeline = MedicalCodingPipeline.load("./path/to/production/model")

        cda_response = pipeline(test_cda_request)

        assert isinstance(cda_response, CdaResponse)

        assert "Aspirin" in cda_response.document
        assert "Hypertension" in cda_response.document
        assert "Allergy to peanuts" in cda_response.document
