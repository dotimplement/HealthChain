import pytest

from healthchain.io.containers import Document
from healthchain.models.responses.cdsresponse import Action, CDSResponse, Card
from healthchain.models.data.cdsfhirdata import CdsFhirData


def test_input_with_valid_prefetch(cds_fhir_connector, test_cds_request):
    # Use the valid prefetch data from test_cds_request
    input_data = test_cds_request

    # Call the input method
    result = cds_fhir_connector.input(input_data)

    # Assert the result
    assert isinstance(result, Document)
    assert result.data == str(input_data.prefetch)
    assert isinstance(result.fhir_resources, CdsFhirData)
    assert result.fhir_resources.context == input_data.context.model_dump()
    assert result.fhir_resources.model_dump_prefetch() == input_data.prefetch


def test_output_with_cards(cds_fhir_connector):
    # Prepare test data
    cards = [
        Card(
            summary="Test Card 1",
            detail="This is a test card",
            indicator="info",
            source={"label": "Test Source"},
        ),
        Card(
            summary="Test Card 2",
            detail="This is another test card",
            indicator="warning",
            source={"label": "Test Source"},
        ),
    ]
    actions = [
        Action(
            type="create",
            description="Create a new resource",
            resource={"resourceType": "Patient", "id": "123"},
            resourceId="123",
        )
    ]
    out_data = Document(data="", cds_cards=cards, cds_actions=actions)

    # Call the output method
    result = cds_fhir_connector.output(out_data)

    # Assert the result
    assert isinstance(result, CDSResponse)
    assert result.cards == cards
    assert result.systemActions == actions


def test_output_without_cards(cds_fhir_connector, caplog):
    # Prepare test data
    out_data = Document(data="", cds_cards=None)

    # Call the output method
    result = cds_fhir_connector.output(out_data)

    # Assert the result
    assert isinstance(result, CDSResponse)
    assert result.cards == []
    assert result.systemActions is None
    assert (
        "No CDS cards found in Document, returning empty list of cards" in caplog.text
    )


def test_input_with_empty_request(cds_fhir_connector, test_cds_request):
    # Prepare test data
    input_data = test_cds_request
    input_data.prefetch = None
    input_data.fhirServer = None

    # Call the input method and expect a ValueError
    with pytest.raises(ValueError) as exc_info:
        cds_fhir_connector.input(input_data)

    # Assert the error message
    assert (
        str(exc_info.value)
        == "Either prefetch or fhirServer must be provided to extract FHIR data!"
    )


def test_input_with_fhir_server(cds_fhir_connector, test_cds_request):
    # Prepare test data
    input_data = test_cds_request
    input_data.prefetch = None
    input_data.fhirServer = "http://example.com/fhir"

    # Call the input method and expect a NotImplementedError
    with pytest.raises(NotImplementedError) as exc_info:
        cds_fhir_connector.input(input_data)

    # Assert the error message
    assert str(exc_info.value) == "FHIR server is not implemented yet!"
