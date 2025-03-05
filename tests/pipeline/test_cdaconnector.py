from unittest.mock import Mock, patch
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.io.containers import Document


@patch("healthchain.io.cdaconnector.CdaAnnotator")
def test_input(
    mock_annotator_class,
    cda_connector,
    test_condition,
    test_medication,
    test_allergy,
):
    # Create mock CDA document with FHIR resources
    mock_cda_doc = Mock()
    mock_cda_doc.problem_list = [test_condition]
    mock_cda_doc.medication_list = [test_medication]
    mock_cda_doc.allergy_list = [test_allergy]
    mock_cda_doc.note = "Test note"

    # Set up the mock annotator
    mock_annotator_class.from_xml.return_value = mock_cda_doc

    input_data = CdaRequest(document="<xml>Test CDA</xml>")
    result = cda_connector.input(input_data)

    assert isinstance(result, Document)
    assert result.data == "Test note"

    # Verify documents in FHIR bundle
    documents = result.fhir.get_document_references_readable()
    assert len(documents) == 2

    # Verify original CDA document
    assert (
        documents[0]["description"] == "Original CDA Document processed by HealthChain"
    )
    assert documents[0]["attachments"][0]["data"] == "<xml>Test CDA</xml>"
    assert documents[0]["attachments"][0]["metadata"]["content_type"] == "text/xml"
    assert (
        documents[0]["attachments"][0]["metadata"]["title"]
        == "Original CDA document in XML format"
    )

    # Verify extracted note document
    assert (
        documents[1]["description"]
        == "Text from note section of related CDA document extracted by HealthChain"
    )
    assert documents[1]["attachments"][0]["data"] == "Test note"
    assert documents[1]["attachments"][0]["metadata"]["content_type"] == "text/plain"
    assert (
        documents[1]["attachments"][0]["metadata"]["title"]
        == "Note text from the related CDA document"
    )

    # Verify document relationship
    assert len(documents[1]["relationships"]["parents"]) == 1
    assert documents[1]["relationships"]["parents"][0]["id"] == documents[0]["id"]

    # Verify FHIR resources
    assert len(result.fhir.problem_list) == 1
    assert result.fhir.problem_list[0].code.coding[0].code == "123"

    assert len(result.fhir.medication_list) == 1
    assert result.fhir.medication_list[0].medication.concept.coding[0].code == "456"

    assert len(result.fhir.allergy_list) == 1
    assert result.fhir.allergy_list[0].code.coding[0].code == "789"


def test_output(cda_connector, test_condition, test_medication, test_allergy):
    cda_connector.cda_doc = Mock()
    cda_connector.cda_doc.export.return_value = "<xml>Updated CDA</xml>"

    # Create a document with FHIR resources
    out_data = Document(data="Updated note")
    out_data.fhir.problem_list = [test_condition]
    out_data.fhir.medication_list = [test_medication]
    out_data.fhir.allergy_list = [test_allergy]

    result = cda_connector.output(out_data)

    assert isinstance(result, CdaResponse)
    assert result.document == "<xml>Updated CDA</xml>"

    # Verify that the CDA document was updated with FHIR resources
    cda_connector.cda_doc.add_to_problem_list.assert_called_once_with(
        out_data.fhir.problem_list, overwrite=False
    )
    cda_connector.cda_doc.add_to_allergy_list.assert_called_once_with(
        out_data.fhir.allergy_list, overwrite=False
    )
    cda_connector.cda_doc.add_to_medication_list.assert_called_once_with(
        out_data.fhir.medication_list, overwrite=False
    )
