import pytest
from healthchain.pipeline.components.fhirproblemextractor import (
    FHIRProblemListExtractor,
)
from healthchain.io.containers import Document


def test_extracts_conditions_from_generic_entities():
    """ProblemListExtractor extracts conditions from entities with medical codes."""
    doc = Document(data="Patient has fever")
    doc.nlp.set_entities([{"text": "fever", "cui": "C0015967"}])

    extractor = FHIRProblemListExtractor(patient_ref="Patient/test")
    result = extractor(doc)

    assert len(result.fhir.problem_list) == 1
    condition = result.fhir.problem_list[0]
    assert condition.subject.reference == "Patient/test"
    assert condition.code.coding[0].code == "C0015967"


@pytest.mark.parametrize(
    "code_attribute,code_value",
    [
        ("cui", "C0015967"),
        ("snomed_id", "386661006"),
        ("icd10", "R50.9"),
    ],
)
def test_supports_different_code_attributes(code_attribute, code_value):
    """ProblemListExtractor supports multiple medical coding systems."""
    doc = Document(data="Test")
    entities = [{"text": "fever", code_attribute: code_value}]
    doc.nlp.set_entities(entities)

    extractor = FHIRProblemListExtractor(code_attribute=code_attribute)
    result = extractor(doc)

    assert len(result.fhir.problem_list) == 1
    assert result.fhir.problem_list[0].code.coding[0].code == code_value


def test_skips_entities_without_codes():
    """ProblemListExtractor skips entities without medical codes."""
    doc = Document(data="Test")
    entities = [
        {"text": "fever", "cui": "C0015967"},  # Valid
        {"text": "patient"},  # No code
        {"text": "cough", "cui": None},  # Null code
    ]
    doc.nlp.set_entities(entities)

    extractor = FHIRProblemListExtractor()
    result = extractor(doc)

    assert len(result.fhir.problem_list) == 1
    assert result.fhir.problem_list[0].code.coding[0].code == "C0015967"


def test_preserves_existing_conditions(test_condition):
    """ProblemListExtractor preserves existing conditions."""
    doc = Document(data="Test")
    doc.fhir.problem_list = [test_condition]
    doc.nlp.set_entities([{"text": "fever", "cui": "C0015967"}])

    extractor = FHIRProblemListExtractor()
    result = extractor(doc)

    assert len(result.fhir.problem_list) == 2
    assert test_condition in result.fhir.problem_list
