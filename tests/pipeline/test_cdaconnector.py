from unittest.mock import Mock, patch
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.io.containers import Document
from fhir.resources.documentreference import DocumentReference


@patch("healthchain.io.cdaconnector.create_engine")
@patch("healthchain.io.cdaconnector.create_document_reference")
@patch("healthchain.io.cdaconnector.read_content_attachment")
@patch("healthchain.io.cdaconnector.set_problem_list_item_category")
@patch("healthchain.io.cdaconnector.Document", autospec=True)
def test_input(
    mock_document_class,
    mock_set_problem_category,
    mock_read_content,
    mock_create_doc_ref,
    mock_create_engine,
    cda_connector,
    test_condition,
    test_medication,
    test_allergy,
):
    # Create mock engine
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine

    # Mock document reference content extraction
    mock_read_content.return_value = [{"data": "Extracted note text"}]

    # Create mock document and mock document's fhir attribute
    mock_doc = Mock(spec=Document)
    mock_doc.fhir = Mock()
    mock_doc.fhir.bundle = Mock()
    mock_doc.fhir.problem_list = []
    mock_doc.fhir.medication_list = []
    mock_doc.fhir.allergy_list = []
    mock_doc.fhir.add_document_reference = Mock()

    # Configure the mock Document class to return our mock document
    mock_document_class.return_value = mock_doc

    # Configure the mock document references
    cda_doc_ref = Mock()
    cda_doc_ref.id = "cda-doc-ref"

    # Create a proper DocumentReference mock that matches what the code expects
    note_doc_ref = Mock(spec=DocumentReference)
    note_doc_ref.id = "note-doc-ref"
    note_doc_ref.content = [Mock()]
    note_doc_ref.content[0].attachment = Mock()
    note_doc_ref.content[0].attachment.data = b"encoded data"

    # Configure create_document_reference to return cda_doc_ref
    mock_create_doc_ref.return_value = cda_doc_ref

    # Configure the mock engine to return test resources including the DocumentReference
    mock_engine.to_fhir.return_value = [
        test_condition,
        test_medication,
        test_allergy,
        note_doc_ref,
    ]

    # Call the method
    cda_connector.engine = mock_engine
    input_data = CdaRequest(document="<xml>Test CDA</xml>")
    result = cda_connector.input(input_data)

    # 1. Verify the engine was called correctly to convert CDA to FHIR
    mock_engine.to_fhir.assert_called_once_with(
        "<xml>Test CDA</xml>", src_format=mock_engine.to_fhir.call_args[1]["src_format"]
    )

    # 2. Verify document reference was created for original CDA
    mock_create_doc_ref.assert_called_once_with(
        data="<xml>Test CDA</xml>",
        content_type="text/xml",
        description="Original CDA Document processed by HealthChain",
        attachment_title="Original CDA document in XML format",
    )

    # 3. Verify note_document_reference was set correctly
    assert cda_connector.note_document_reference == note_doc_ref

    # 4. Verify document references were added to the Document
    assert mock_doc.fhir.add_document_reference.call_count == 2
    mock_doc.fhir.add_document_reference.assert_any_call(cda_doc_ref)
    mock_doc.fhir.add_document_reference.assert_any_call(
        note_doc_ref, parent_id=cda_doc_ref.id
    )

    # 5. Verify resources were sorted into appropriate lists
    assert mock_doc.fhir.problem_list == [test_condition]
    assert mock_doc.fhir.medication_list == [test_medication]
    assert mock_doc.fhir.allergy_list == [test_allergy]

    # 6. Verify problem list items were categorized
    mock_set_problem_category.assert_called_once_with(test_condition)

    # 7. Verify document reference content was read
    mock_read_content.assert_called_once_with(note_doc_ref)

    # 8. Verify document data was set to the extracted text
    assert mock_doc.data == "Extracted note text"

    # 9. Verify that the document was returned
    assert result is mock_doc


@patch("healthchain.io.cdaconnector.create_engine")
def test_output(
    mock_create_engine, cda_connector, test_condition, test_medication, test_allergy
):
    # Create mock engine
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine

    # Configure mock engine to return CDA XML
    mock_engine.from_fhir.return_value = "<xml>Updated CDA</xml>"

    # Set the connector's engine and original CDA
    cda_connector.engine = mock_engine
    cda_connector.original_cda = "<xml>Original CDA</xml>"

    # Create a mock document reference for the note
    note_doc_ref = Mock()
    note_doc_ref.id = "note-doc-ref"
    cda_connector.note_document_reference = note_doc_ref

    # Create a document with FHIR resources
    out_data = Document(data="Updated note")
    out_data.fhir.problem_list = [test_condition]
    out_data.fhir.medication_list = [test_medication]
    out_data.fhir.allergy_list = [test_allergy]

    # Call the output method
    result = cda_connector.output(out_data)

    # 1. Verify the correct response type is returned
    assert isinstance(result, CdaResponse)
    assert result.document == "<xml>Updated CDA</xml>"

    # 2. Verify the engine was called correctly to convert FHIR to CDA
    mock_engine.from_fhir.assert_called_once()

    # 3. Verify all resources were passed to from_fhir including the note document reference
    resources_passed = mock_engine.from_fhir.call_args[0][0]
    assert len(resources_passed) == 4  # 3 clinical resources + 1 document reference
    assert test_condition in resources_passed
    assert test_medication in resources_passed
    assert test_allergy in resources_passed
    assert note_doc_ref in resources_passed
