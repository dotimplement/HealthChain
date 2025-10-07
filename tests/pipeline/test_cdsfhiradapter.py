import pytest

from healthchain.io.containers import Document
from healthchain.io.containers.document import CdsAnnotations
from healthchain.models.responses.cdsresponse import Action, CDSResponse, Card
from fhir.resources.resource import Resource
from fhir.resources.documentreference import DocumentReference


def test_parse_with_no_document_reference(cds_fhir_adapter, test_cds_request):
    # Use the valid prefetch data from test_cds_request
    input_data = test_cds_request

    # Call the input method
    result = cds_fhir_adapter.parse(input_data)

    # Assert the result
    assert isinstance(result, Document)
    assert (
        result.data == ""
    )  # Data should be empty since no DocumentReference is provided
    assert all(
        isinstance(resource, Resource)
        for resource in result.fhir._prefetch_resources.values()
    )


def test_parse_with_document_reference(
    cds_fhir_adapter, test_cds_request, doc_ref_with_content
):
    # Add DocumentReference to prefetch data
    test_cds_request.prefetch["document"] = doc_ref_with_content.model_dump(
        exclude_none=True
    )

    # Call the input method
    result = cds_fhir_adapter.parse(test_cds_request)

    # Assert the result
    assert isinstance(result, Document)
    assert isinstance(result.fhir._prefetch_resources["document"], DocumentReference)
    assert result.data == "Test document content"


def test_parse_with_multiple_attachments(
    cds_fhir_adapter, test_cds_request, doc_ref_with_multiple_content
):
    # Add DocumentReference to prefetch data
    test_cds_request.prefetch["document"] = doc_ref_with_multiple_content.model_dump(
        exclude_none=True
    )

    # Call the input method
    result = cds_fhir_adapter.parse(test_cds_request)

    # Assert the result
    assert isinstance(result, Document)
    assert (
        result.data == "First content\nSecond content\n"
    )  # Attachments should be concatenated
    assert isinstance(result.fhir._prefetch_resources["document"], DocumentReference)
    assert (
        result.fhir._prefetch_resources["document"]
        .content[0]
        .attachment.data.decode("utf-8")
        == "First content"
    )
    assert (
        result.fhir._prefetch_resources["document"]
        .content[1]
        .attachment.data.decode("utf-8")
        == "Second content"
    )


def test_parse_with_custom_document_key(
    cds_fhir_adapter, test_cds_request, doc_ref_with_content
):
    # Add DocumentReference to prefetch data with custom key
    test_cds_request.prefetch["custom_key"] = doc_ref_with_content.model_dump(
        exclude_none=True
    )

    # Call the input method with custom key
    result = cds_fhir_adapter.parse(
        test_cds_request, prefetch_document_key="custom_key"
    )

    # Assert the result
    assert isinstance(result, Document)
    assert result.data == "Test document content"
    assert isinstance(result.fhir._prefetch_resources["custom_key"], DocumentReference)


def test_parse_with_document_reference_error(
    cds_fhir_adapter, test_cds_request, doc_ref_without_content, caplog
):
    # Add invalid DocumentReference to prefetch data
    test_cds_request.prefetch["document"] = doc_ref_without_content.model_dump(
        exclude_none=True
    )

    # Call the input method
    result = cds_fhir_adapter.parse(test_cds_request)

    # Assert the result
    assert isinstance(result, Document)
    assert result.data == ""  # Should be empty due to error
    assert "Error extracting text from DocumentReference" in caplog.text


def test_parse_with_missing_document_reference(
    cds_fhir_adapter, test_cds_request, caplog
):
    # Call the input method (document key doesn't exist in prefetch)
    result = cds_fhir_adapter.parse(
        test_cds_request, prefetch_document_key="nonexistent"
    )

    # Assert the result
    assert isinstance(result, Document)
    assert result.data == ""
    assert (
        "No DocumentReference resource found in prefetch data with key nonexistent"
        in caplog.text
    )


def test_format_with_cards(cds_fhir_adapter):
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
    out_data = Document(data="", _cds=CdsAnnotations(_cards=cards, _actions=actions))

    # Call the output method
    result = cds_fhir_adapter.format(out_data)

    # Assert the result
    assert isinstance(result, CDSResponse)
    assert result.cards == cards
    assert result.systemActions == actions


def test_format_without_cards(cds_fhir_adapter, caplog):
    # Prepare test data
    out_data = Document(data="", _cds=CdsAnnotations(_cards=None, _actions=None))

    # Call the output method
    result = cds_fhir_adapter.format(out_data)

    # Assert the result
    assert isinstance(result, CDSResponse)
    assert result.cards == []
    assert result.systemActions is None
    assert (
        "No CDS cards found in Document, returning empty list of cards" in caplog.text
    )


def test_parse_with_empty_request(cds_fhir_adapter, test_cds_request):
    # Prepare test data
    input_data = test_cds_request
    input_data.prefetch = None
    input_data.fhirServer = None

    # Call the input method and expect a ValueError
    with pytest.raises(ValueError) as exc_info:
        cds_fhir_adapter.parse(input_data)

    # Assert the error message
    assert (
        str(exc_info.value)
        == "Either prefetch or fhirServer must be provided to extract FHIR data!"
    )


def test_parse_with_fhir_server(cds_fhir_adapter, test_cds_request):
    # Prepare test data
    input_data = test_cds_request
    input_data.prefetch = None
    input_data.fhirServer = "http://example.com/fhir"

    # Call the input method and expect a NotImplementedError
    with pytest.raises(NotImplementedError) as exc_info:
        cds_fhir_adapter.parse(input_data)

    # Assert the error message
    assert str(exc_info.value) == "FHIR server is not implemented yet!"
