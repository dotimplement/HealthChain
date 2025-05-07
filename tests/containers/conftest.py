import pytest
from healthchain.io.containers.document import FhirData, Document
from healthchain.fhir import create_bundle, create_document_reference


@pytest.fixture
def fhir_data():
    return FhirData()


@pytest.fixture
def sample_bundle():
    return create_bundle()


@pytest.fixture
def sample_document():
    return Document("This is a sample text for testing.")


@pytest.fixture
def sample_document_reference():
    return create_document_reference(
        data="test content",
        content_type="text/plain",
        description="Test Document",
    )


@pytest.fixture
def document_family():
    """Create a family of related documents."""
    original = create_document_reference(
        data="original content",
        content_type="text/plain",
        description="Original Report",
    )

    summary = create_document_reference(
        data="summary content", content_type="text/plain", description="Summary"
    )

    translation = create_document_reference(
        data="translated content", content_type="text/plain", description="Translation"
    )

    return original, summary, translation
