from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.documentreference import DocumentReference
from fhir.resources.attachment import Attachment
from fhir.resources.coding import Coding
from datetime import datetime


from healthchain.fhir import (
    create_resource_from_dict,
    create_single_codeable_concept,
    create_single_reaction,
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
    set_condition_category,
    create_single_attachment,
    create_document_reference,
    create_document_reference_content,
    read_content_attachment,
    add_provenance_metadata,
    add_coding_to_codeable_concept,
    calculate_age_from_birthdate,
    calculate_age_from_event_date,
)
import pytest


def test_create_single_codeable_concept():
    """Test creating a CodeableConcept with a single coding."""
    concept = create_single_codeable_concept(
        code="123",
        display="Test Concept",
    )

    assert isinstance(concept, CodeableConcept)
    assert len(concept.coding) == 1
    assert concept.coding[0].code == "123"
    assert concept.coding[0].display == "Test Concept"
    assert concept.coding[0].system == "http://snomed.info/sct"


def test_create_single_reaction():
    """Test creating a reaction with severity."""
    reaction = create_single_reaction(
        code="123",
        display="Test Reaction",
        system="http://test.system",
        severity="severe",
    )

    assert isinstance(reaction, list)
    assert len(reaction) == 1
    assert reaction[0]["severity"] == "severe"
    assert len(reaction[0]["manifestation"]) == 1
    assert isinstance(reaction[0]["manifestation"][0], CodeableReference)
    assert reaction[0]["manifestation"][0].concept.coding[0].code == "123"
    assert reaction[0]["manifestation"][0].concept.coding[0].display == "Test Reaction"
    assert (
        reaction[0]["manifestation"][0].concept.coding[0].system == "http://test.system"
    )


def test_create_condition():
    """Test creating a condition with all optional fields."""
    condition = create_condition(
        subject="Patient/123",
        clinical_status="resolved",
        code="123",
        display="Test Condition",
        system="http://test.system",
    )

    assert isinstance(condition, Condition)
    assert condition.id.startswith("hc-")
    assert len(condition.id) > 3  # Ensure there's content after "hc-"
    assert condition.subject.reference == "Patient/123"
    assert condition.clinicalStatus.coding[0].code == "resolved"
    assert condition.code.coding[0].code == "123"
    assert condition.code.coding[0].display == "Test Condition"
    assert condition.code.coding[0].system == "http://test.system"

    set_condition_category(condition, "problem-list-item")
    assert condition.category[0].coding[0].code == "problem-list-item"


def test_create_medication_statement_minimal():
    """Test creating a medication statement with only required fields."""
    medication = create_medication_statement(
        subject="Patient/123",
        code="123",
        display="Test Medication",
        system="http://test.system",
    )

    assert isinstance(medication, MedicationStatement)
    assert medication.id.startswith("hc-")
    assert len(medication.id) > 3  # Ensure there's content after "hc-"
    assert medication.subject.reference == "Patient/123"
    assert medication.status == "recorded"
    assert medication.medication.concept.coding[0].code == "123"
    assert medication.medication.concept.coding[0].display == "Test Medication"
    assert medication.medication.concept.coding[0].system == "http://test.system"


def test_create_allergy_intolerance_minimal():
    """Test creating an allergy intolerance with only required fields."""
    allergy = create_allergy_intolerance(
        patient="Patient/123",
        code="123",
        display="Test Allergy",
        system="http://test.system",
    )

    assert isinstance(allergy, AllergyIntolerance)
    assert allergy.id.startswith("hc-")
    assert len(allergy.id) > 3  # Ensure there's content after "hc-"
    assert allergy.patient.reference == "Patient/123"
    assert allergy.code.coding[0].code == "123"
    assert allergy.code.coding[0].display == "Test Allergy"
    assert allergy.code.coding[0].system == "http://test.system"


def test_create_single_attachment():
    """Test creating an attachment with data content."""
    attachment = create_single_attachment(
        content_type="text/plain", data="Test content", title="Test Attachment"
    )

    assert isinstance(attachment, Attachment)
    assert attachment.contentType == "text/plain"
    assert attachment.title == "Test Attachment"
    # Verify data is base64 encoded
    assert attachment.data is not None
    assert isinstance(attachment.data, bytes)
    # Verify creation date is set
    assert attachment.creation is not None
    assert isinstance(attachment.creation, datetime)


def test_create_single_attachment_with_url():
    """Test creating an attachment with URL reference."""
    attachment = create_single_attachment(
        content_type="application/pdf",
        url="http://example.com/test.pdf",
        title="Test URL Attachment",
    )

    assert isinstance(attachment, Attachment)
    assert attachment.contentType == "application/pdf"
    assert attachment.url == "http://example.com/test.pdf"
    assert attachment.title == "Test URL Attachment"
    assert attachment.data is None


def test_create_document_reference():
    """Test creating a document reference with data content."""
    doc_ref = create_document_reference(
        data="Test document content",
        content_type="text/plain",
        description="Test Description",
        attachment_title="Test Doc",
    )

    assert isinstance(doc_ref, DocumentReference)
    assert doc_ref.id.startswith("hc-")
    assert len(doc_ref.id) > 3  # Ensure there's content after "hc-"
    assert doc_ref.status == "current"
    assert doc_ref.description == "Test Description"
    assert len(doc_ref.content) == 1
    assert doc_ref.content[0].attachment.contentType == "text/plain"
    assert doc_ref.content[0].attachment.title == "Test Doc"
    assert doc_ref.content[0].attachment.data is not None
    assert isinstance(doc_ref.content[0].attachment.data, bytes)
    # Verify date is set
    assert doc_ref.date is not None
    assert isinstance(doc_ref.date, datetime)


def test_create_document_reference_with_url():
    """Test creating a document reference with URL reference."""
    doc_ref = create_document_reference(
        url="http://example.com/test.pdf",
        content_type="application/pdf",
        status="superseded",
    )

    assert isinstance(doc_ref, DocumentReference)
    assert doc_ref.id.startswith("hc-")
    assert len(doc_ref.id) > 3  # Ensure there's content after "hc-"
    assert doc_ref.status == "superseded"
    assert len(doc_ref.content) == 1
    assert doc_ref.content[0].attachment.contentType == "application/pdf"
    assert doc_ref.content[0].attachment.url == "http://example.com/test.pdf"
    assert doc_ref.content[0].attachment.data is None


def test_read_attachment_with_data():
    """Test reading an attachment with embedded data content."""
    # Create a document reference with data content
    test_content = "Test document content"
    doc_ref = create_document_reference(
        data=test_content,
        content_type="text/plain",
        description="Test Description",
        attachment_title="Test Doc",
    )

    # Test reading attachments
    attachments = read_content_attachment(doc_ref)
    assert isinstance(attachments, list)
    assert len(attachments) == 1
    assert attachments[0]["data"] == test_content
    assert attachments[0]["metadata"]["content_type"] == "text/plain"
    assert attachments[0]["metadata"]["title"] == "Test Doc"
    assert attachments[0]["metadata"]["creation"] is not None

    # Test reading without content
    attachments = read_content_attachment(doc_ref, include_data=False)
    assert isinstance(attachments, list)
    assert len(attachments) == 1
    assert "data" not in attachments[0]
    assert attachments[0]["metadata"]["content_type"] == "text/plain"
    assert attachments[0]["metadata"]["title"] == "Test Doc"
    assert attachments[0]["metadata"]["creation"] is not None


def test_read_attachment_with_url():
    """Test reading an attachment with URL reference."""
    # Create a document reference with URL
    test_url = "http://example.com/test.pdf"
    doc_ref = create_document_reference(
        url=test_url, content_type="application/pdf", attachment_title="Test URL Doc"
    )

    # Test reading attachments
    attachments = read_content_attachment(doc_ref)
    assert isinstance(attachments, list)
    assert len(attachments) == 1
    assert attachments[0]["data"] == test_url
    assert attachments[0]["metadata"]["content_type"] == "application/pdf"
    assert attachments[0]["metadata"]["title"] == "Test URL Doc"
    assert attachments[0]["metadata"]["creation"] is not None

    # Test reading without content
    attachments = read_content_attachment(doc_ref, include_data=False)
    assert isinstance(attachments, list)
    assert len(attachments) == 1
    assert "data" not in attachments[0]
    assert attachments[0]["metadata"]["content_type"] == "application/pdf"
    assert attachments[0]["metadata"]["title"] == "Test URL Doc"
    assert attachments[0]["metadata"]["creation"] is not None


def test_create_document_reference_content_with_data():
    """Test creating DocumentReferenceContent with inline data."""
    content = create_document_reference_content(
        attachment_data="Test data", content_type="text/plain", title="Test Document"
    )

    assert "attachment" in content
    assert content["attachment"].contentType == "text/plain"
    assert content["attachment"].title == "Test Document"
    assert content["attachment"].data is not None
    assert content["language"] == "en-US"


def test_create_document_reference_content_with_url():
    """Test creating DocumentReferenceContent with URL."""
    content = create_document_reference_content(
        url="https://example.com/doc.pdf",
        content_type="application/pdf",
        title="External Document",
    )

    assert "attachment" in content
    assert content["attachment"].url == "https://example.com/doc.pdf"
    assert content["attachment"].contentType == "application/pdf"


def test_create_document_reference_content_custom_language():
    """Test creating DocumentReferenceContent with custom language."""
    content = create_document_reference_content(
        attachment_data="Données de test", language="fr-FR"
    )

    assert content["language"] == "fr-FR"


def test_create_document_reference_content_with_kwargs():
    """Test creating DocumentReferenceContent with additional fields."""
    content = create_document_reference_content(
        attachment_data="Test",
        format=Coding(
            system="http://ihe.net/fhir/ValueSet/IHE.FormatCode.codesystem",
            code="urn:ihe:pcc:handp:2008",
        ),
    )

    assert "format" in content


def test_create_resource_from_dict_success_and_failure():
    cond_dict = {
        "id": "x",
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "subject": {"reference": "Patient/1"},
    }
    ok = create_resource_from_dict(cond_dict, "Condition")
    assert ok is not None
    bad = create_resource_from_dict({}, "NotAType")
    assert bad is None


def test_add_provenance_metadata_sets_source_and_tag():
    cond = create_condition(subject="Patient/1", code="E11.9")
    updated = add_provenance_metadata(cond, "epic", "aggregated", "Aggregated")
    assert updated.meta.source.endswith(":epic")
    assert updated.meta.lastUpdated is not None
    assert any(t.code == "aggregated" for t in (updated.meta.tag or []))


def test_add_coding_to_codeable_concept_appends():
    cc = create_single_codeable_concept("123", "X")
    updated = add_coding_to_codeable_concept(cc, "456", "http://sys", "Y")
    assert any(c.code == "456" and c.system == "http://sys" for c in updated.coding)


def test_set_condition_category_invalid_raises():
    cond = create_condition(subject="Patient/1", code="E11.9")
    with pytest.raises(ValueError):
        set_condition_category(cond, "not-valid")


def test_create_condition_without_code_is_none():
    cond = create_condition(subject="Patient/1")
    assert cond.code is None


def test_calculate_age_from_birthdate():
    """Test standard age calculation from birth date."""
    # Test with date 30 years ago
    from datetime import datetime

    birth_year = datetime.now().year - 30
    birth_date = f"{birth_year}-06-15"

    age = calculate_age_from_birthdate(birth_date)
    assert age is not None
    # Age should be 29 or 30 depending on current date
    assert age in [29, 30]


def test_calculate_age_from_birthdate_with_full_datetime():
    """Test age calculation with full ISO datetime."""
    from datetime import datetime

    birth_year = datetime.now().year - 25
    birth_date = f"{birth_year}-03-10T10:30:00Z"

    age = calculate_age_from_birthdate(birth_date)
    assert age is not None
    assert age in [24, 25]


def test_calculate_age_from_birthdate_invalid():
    """Test age calculation with invalid date."""
    assert calculate_age_from_birthdate(None) is None
    assert calculate_age_from_birthdate("") is None
    assert calculate_age_from_birthdate("invalid") is None


def test_calculate_age_from_event_date():
    """Test MIMIC-IV style age calculation using event date."""
    birth_date = "1990-06-15"
    event_date = "2020-03-10"

    age = calculate_age_from_event_date(birth_date, event_date)
    assert age == 30  # 2020 - 1990 = 30


def test_calculate_age_from_event_date_with_full_datetime():
    """Test MIMIC-IV style calculation with full ISO datetime."""
    birth_date = "1985-12-25T08:00:00Z"
    event_date = "2023-01-15T14:30:00Z"

    age = calculate_age_from_event_date(birth_date, event_date)
    assert age == 38  # 2023 - 1985 = 38


def test_calculate_age_from_event_date_same_year():
    """Test MIMIC-IV style calculation when birth and event in same year."""
    birth_date = "2020-01-01"
    event_date = "2020-12-31"

    age = calculate_age_from_event_date(birth_date, event_date)
    assert age == 0  # Same year = 0


def test_calculate_age_from_event_date_invalid():
    """Test MIMIC-IV style calculation with invalid dates."""
    assert calculate_age_from_event_date(None, "2020-01-01") is None
    assert calculate_age_from_event_date("1990-01-01", None) is None
    assert calculate_age_from_event_date("", "2020-01-01") is None
    assert calculate_age_from_event_date("invalid", "2020-01-01") is None
    assert calculate_age_from_event_date("1990-01-01", "invalid") is None
