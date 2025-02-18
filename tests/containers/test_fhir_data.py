from healthchain.fhir import create_condition, create_document_reference


def test_bundle_operations(fhir_data, sample_bundle):
    """Test basic bundle operations."""
    assert fhir_data.get_bundle() is None

    fhir_data.set_bundle(sample_bundle)
    assert fhir_data.get_bundle() == sample_bundle


def test_cds_context_operations(fhir_data):
    """Test CDS context operations."""
    assert fhir_data.get_cds_context() is None

    test_context = {"hook": "patient-view", "hookInstance": "123"}
    fhir_data.set_cds_context(test_context)
    assert fhir_data.get_cds_context() == test_context


def test_resource_operations(fhir_data):
    """Test adding and getting generic resources."""
    # Create test conditions
    condition1 = create_condition(
        subject="Patient/123", code="C1", display="Test Condition 1"
    )
    condition2 = create_condition(
        subject="Patient/123", code="C2", display="Test Condition 2"
    )

    # Test empty resource list
    assert len(fhir_data.get_resources("Condition")) == 0

    # Test adding resources
    fhir_data.add_resources([condition1, condition2], "Condition")
    resources = fhir_data.get_resources("Condition")
    assert len(resources) == 2

    # Test replace flag
    condition3 = create_condition(
        subject="Patient/123", code="C3", display="Test Condition 3"
    )
    fhir_data.add_resources([condition3], "Condition", replace=True)
    resources = fhir_data.get_resources("Condition")
    assert len(resources) == 1
    assert resources[0].code.coding[0].code == "C3"


def test_document_relationships(fhir_data, document_family):
    """Test document relationship tracking."""
    original, summary, translation = document_family

    # Add documents with relationships
    original_id = fhir_data.add_document(original)
    summary_id = fhir_data.add_document(summary, parent_id=original_id)
    fhir_data.add_document(translation, parent_id=original_id)

    # Test original document family
    original_family = fhir_data.get_document_family(original_id)
    assert original_family["document"].description == "Original Report"
    assert len(original_family["children"]) == 2
    assert len(original_family["parents"]) == 0
    assert len(original_family["siblings"]) == 0

    # Test child document family
    summary_family = fhir_data.get_document_family(summary_id)
    assert len(summary_family["parents"]) == 1
    assert summary_family["parents"][0].description == "Original Report"
    assert len(summary_family["siblings"]) == 1
    assert summary_family["siblings"][0].description == "Translation"


def test_get_documents_output(fhir_data, document_family):
    """Test document retrieval with various options."""
    original, summary, translation = document_family

    # Add documents with relationships
    original_id = fhir_data.add_document(original)
    summary_id = fhir_data.add_document(summary, parent_id=original_id)
    fhir_data.add_document(translation, parent_id=original_id)

    # Test basic document retrieval
    docs = fhir_data.get_documents(include_data=False, include_relationships=False)
    assert len(docs) == 3
    for doc in docs:
        assert "id" in doc
        assert "description" in doc
        assert "status" in doc
        assert "data" not in doc
        assert "relationships" not in doc

    # Test with content
    docs = fhir_data.get_documents(include_data=True, include_relationships=False)
    assert len(docs) == 3
    for doc in docs:
        assert "attachments" in doc
        assert len(doc["attachments"]) > 0
        assert "data" in doc["attachments"][0]
        assert "metadata" in doc["attachments"][0]

    original_doc = next(d for d in docs if d["id"] == original_id)
    assert original_doc["attachments"][0]["data"] == "original content"

    # Test with relationships
    docs = fhir_data.get_documents(include_data=False, include_relationships=True)
    original_doc = next(d for d in docs if d["id"] == original_id)
    summary_doc = next(d for d in docs if d["id"] == summary_id)

    assert len(original_doc["relationships"]["children"]) == 2
    assert len(summary_doc["relationships"]["siblings"]) == 1
    assert len(summary_doc["relationships"]["parents"]) == 1


def test_document_not_found(fhir_data):
    """Test behavior when requesting non-existent document."""
    family = fhir_data.get_document_family("nonexistent-id")
    assert family["document"] is None
    assert len(family["parents"]) == 0
    assert len(family["children"]) == 0
    assert len(family["siblings"]) == 0


def test_relationship_metadata(fhir_data, sample_document_reference):
    """Test the structure of relationship metadata."""
    doc_id = fhir_data.add_document(sample_document_reference)

    child_doc = create_document_reference(
        data="child content",
        content_type="text/plain",
        description="Child Document",
    )

    fhir_data.add_document(child_doc, parent_id=doc_id)

    # Verify relationship structure
    child = fhir_data.get_resources("DocumentReference")[1]
    assert hasattr(child, "relatesTo")
    assert child.relatesTo[0]["code"].coding[0].code == "transforms"
    assert child.relatesTo[0]["code"].coding[0].display == "Transforms"
    assert (
        child.relatesTo[0]["code"].coding[0].system
        == "http://hl7.org/fhir/ValueSet/document-relationship-type"
    )
    assert child.relatesTo[0]["target"]["reference"] == f"DocumentReference/{doc_id}"
