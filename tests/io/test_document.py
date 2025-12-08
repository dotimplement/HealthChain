import pytest

from healthchain.io.containers.document import Document
from unittest.mock import patch, MagicMock
from fhir.resources.bundle import Bundle
from healthchain.fhir import create_bundle, add_resource, create_condition


@pytest.fixture
def sample_document():
    return Document("This is a sample text for testing.")


def test_document_initialization(sample_document):
    """Test basic Document initialization and properties."""
    assert sample_document.data == "This is a sample text for testing."
    assert sample_document.text == "This is a sample text for testing."
    assert sample_document.nlp.get_tokens() == [
        "This",
        "is",
        "a",
        "sample",
        "text",
        "for",
        "testing.",
    ]
    assert sample_document.nlp.get_entities() == []
    assert sample_document.nlp.get_embeddings() is None


@pytest.mark.parametrize(
    "data_builder, expect_bundle, expected_entries, expected_text",
    [
        # bundle with two conditions
        (
            lambda: (
                lambda b: (
                    add_resource(
                        b, create_condition(subject="Patient/123", code="E11.9")
                    ),
                    add_resource(
                        b, create_condition(subject="Patient/123", code="I10")
                    ),
                )
                and b
            )(create_bundle("collection")),
            True,
            2,
            "",
        ),
        # resource list
        (
            lambda: [
                create_condition(subject="Patient/123", code="E11.9"),
                create_condition(subject="Patient/123", code="I10"),
            ],
            True,
            2,
            "",
        ),
        # text only
        (lambda: "Patient has hypertension", False, 0, "Patient has hypertension"),
        # empty list
        (lambda: [], None, 0, ""),
    ],
)
def test_document_handles_various_data_inputs(
    data_builder, expect_bundle, expected_entries, expected_text
):
    """Document handles bundle, resource list, text-only, and empty list inputs."""
    data = data_builder()
    doc = Document(data=data)

    if expect_bundle is True:
        assert isinstance(doc.fhir.bundle, Bundle)
        assert len(doc.fhir.bundle.entry) == expected_entries
        assert doc.text == expected_text
    elif expect_bundle is False:
        assert doc.fhir.bundle is None
        assert doc.text == expected_text
        assert len(doc.nlp._tokens) > 0
    else:
        # empty list case: either no bundle or empty bundle
        assert doc.fhir.bundle is None or len(doc.fhir.bundle.entry) == 0


def test_document_bundle_accessible_via_problem_list():
    """Document's problem_list accessor works with auto-set bundle."""
    bundle = create_bundle("collection")
    add_resource(bundle, create_condition(subject="Patient/123", code="E11.9"))

    doc = Document(data=bundle)

    conditions = doc.fhir.problem_list
    assert len(conditions) == 1
    assert conditions[0].code.coding[0].code == "E11.9"

    assert conditions[0].code.coding[0].code == "E11.9"


@pytest.mark.parametrize(
    "num_outcomes, expected_outcome_count, expected_remaining_entries",
    [
        (0, 0, 2),  # no OperationOutcomes
        (2, 2, 2),  # outcomes extracted, conditions remain
    ],
)
def test_document_operation_outcome_extraction(
    num_outcomes, expected_outcome_count, expected_remaining_entries
):
    from fhir.resources.operationoutcome import OperationOutcome, OperationOutcomeIssue

    bundle = create_bundle("collection")
    add_resource(bundle, create_condition(subject="Patient/123", code="E11.9"))
    add_resource(bundle, create_condition(subject="Patient/123", code="I10"))

    for i in range(num_outcomes):
        add_resource(
            bundle,
            OperationOutcome(
                issue=[
                    OperationOutcomeIssue(
                        severity="information" if i == 0 else "warning",
                        code="informational" if i == 0 else "processing",
                        diagnostics=(
                            "Data retrieved from source A"
                            if i == 0
                            else "Source B temporarily unavailable"
                        ),
                    )
                ]
            ),
        )

    doc = Document(data=bundle)

    assert len(doc.fhir.operation_outcomes) == expected_outcome_count
    assert len(doc.fhir.bundle.entry) == expected_remaining_entries


@pytest.mark.parametrize(
    "num_provenances, expected_provenance_count, expected_remaining_entries",
    [
        (0, 0, 2),  # no Provenances
        (2, 2, 2),  # provenances extracted, conditions remain
    ],
)
def test_document_provenance_extraction(
    num_provenances, expected_provenance_count, expected_remaining_entries
):
    """Document automatically extracts Provenance resources during initialization."""
    from fhir.resources.provenance import Provenance, ProvenanceAgent
    from fhir.resources.reference import Reference

    bundle = create_bundle("collection")
    add_resource(bundle, create_condition(subject="Patient/123", code="E11.9"))
    add_resource(bundle, create_condition(subject="Patient/123", code="I10"))

    for i in range(num_provenances):
        add_resource(
            bundle,
            Provenance(
                target=[Reference(reference=f"Condition/{i}")],
                recorded="2024-01-01T00:00:00Z",
                agent=[
                    ProvenanceAgent(who=Reference(reference=f"Organization/source-{i}"))
                ],
            ),
        )

    doc = Document(data=bundle)

    assert len(doc.fhir.provenances) == expected_provenance_count
    assert len(doc.fhir.bundle.entry) == expected_remaining_entries


@pytest.mark.parametrize("num_patients", [0, 1, 2])
def test_document_patient_convenience_properties_param(num_patients):
    """Patient convenience accessors behave for 0, 1, 2 patients without extraction."""
    from fhir.resources.patient import Patient
    from fhir.resources.humanname import HumanName

    bundle = create_bundle("collection")

    # Add patients
    patients = []
    for i in range(num_patients):
        patient = Patient(
            id=f"patient-{i+1}", name=[HumanName(given=["John"], family=f"Fam{i+1}")]
        )
        patients.append(patient)
        add_resource(bundle, patient)

    # Add a condition referencing first patient if present
    subject_ref = f"Patient/{patients[0].id}" if patients else "Patient/123"
    add_resource(bundle, create_condition(subject=subject_ref, code="E11.9"))

    doc = Document(data=bundle)

    # Singular accessor
    if num_patients >= 1:
        assert doc.fhir.patient is not None
        assert doc.fhir.patient.id == "patient-1"
    else:
        assert doc.fhir.patient is None

    # Plural accessor
    assert len(doc.fhir.patients) == num_patients

    # Patients remain in bundle (no extraction)
    bundle_patients = [
        e.resource
        for e in doc.fhir.bundle.entry
        if type(e.resource).__name__ == "Patient"
    ]
    assert len(bundle_patients) == num_patients


@patch("healthchain.io.containers.document.Span")
def test_update_problem_list_from_nlp(mock_span_class, test_empty_document):
    """Test updating problem list from NLP entities"""

    # Create mock spaCy entities
    mock_ent1 = MagicMock()
    mock_ent1.text = "Hypertension"
    mock_ent1._.cui = "38341003"

    mock_ent2 = MagicMock()
    mock_ent2.text = "Aspirin"
    mock_ent2._.cui = "123454"

    mock_ent3 = MagicMock()
    mock_ent3.text = "Allergy to peanuts"
    mock_ent3._.cui = "70618"

    # Create mock spaCy doc
    mock_spacy_doc = MagicMock()
    mock_spacy_doc.ents = [mock_ent1, mock_ent2, mock_ent3]

    # Add the spaCy doc to the test document
    test_empty_document.nlp.add_spacy_doc(mock_spacy_doc)

    # Update problem list from NLP entities
    test_empty_document.update_problem_list_from_nlp()

    # Verify problems were added correctly
    conditions = test_empty_document.fhir.problem_list
    assert len(conditions) == 3  # All entities are treated as problems by default

    # Check each problem was added with correct attributes
    expected_problems = [
        ("Hypertension", "38341003"),
        ("Aspirin", "123454"),
        ("Allergy to peanuts", "70618"),
    ]

    for i, (text, cui) in enumerate(expected_problems):
        assert conditions[i].code.coding[0].display == text
        assert conditions[i].code.coding[0].code == cui
        assert conditions[i].code.coding[0].system == "http://snomed.info/sct"
