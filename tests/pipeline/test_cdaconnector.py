from unittest.mock import Mock, patch
from healthchain.io.containers.document import HL7Data
from healthchain.models.data.concept import (
    AllergyConcept,
    ConceptLists,
    MedicationConcept,
    ProblemConcept,
)
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.models.data.ccddata import CcdData
from healthchain.io.containers import Document


@patch("healthchain.io.cdaconnector.CdaAnnotator")
def test_input(mock_annotator_class, cda_connector):
    # Create mock CDA document
    mock_cda_doc = Mock()
    mock_cda_doc.problem_list = [ProblemConcept(code="test")]
    mock_cda_doc.medication_list = [MedicationConcept(code="test")]
    mock_cda_doc.allergy_list = [AllergyConcept(code="test")]
    mock_cda_doc.note = "Test note"

    # Set up the mock annotator
    mock_annotator_class.from_xml.return_value = mock_cda_doc

    input_data = CdaRequest(document="<xml>Test CDA</xml>")
    result = cda_connector.input(input_data)

    assert isinstance(result, Document)
    assert result.data == "Test note"

    assert isinstance(result._hl7._ccd_data, CcdData)
    assert result._hl7._ccd_data.concepts.problems == [ProblemConcept(code="test")]
    assert result._hl7._ccd_data.concepts.medications == [
        MedicationConcept(code="test")
    ]
    assert result._hl7._ccd_data.concepts.allergies == [AllergyConcept(code="test")]
    assert result._hl7._ccd_data.note == "Test note"


def test_output(cda_connector):
    cda_connector.cda_doc = Mock()
    cda_connector.cda_doc.export.return_value = "<xml>Updated CDA</xml>"

    out_data = Document(
        data="Updated note",
        _hl7=HL7Data(
            _ccd_data=CcdData(
                concepts=ConceptLists(
                    problems=[ProblemConcept(code="New Problem")],
                    medications=[MedicationConcept(code="New Medication")],
                    allergies=[AllergyConcept(code="New Allergy")],
                ),
                note="Updated note",
            ),
        ),
    )

    result = cda_connector.output(out_data)

    assert isinstance(result, CdaResponse)
    assert result.document == "<xml>Updated CDA</xml>"
    cda_connector.cda_doc.add_to_problem_list.assert_called_once_with(
        [ProblemConcept(code="New Problem")], overwrite=False
    )
    cda_connector.cda_doc.add_to_allergy_list.assert_called_once_with(
        [AllergyConcept(code="New Allergy")], overwrite=False
    )
    cda_connector.cda_doc.add_to_medication_list.assert_called_once_with(
        [MedicationConcept(code="New Medication")], overwrite=False
    )
