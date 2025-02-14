import pytest
from healthchain.fhir.helpers import (
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
)
from healthchain.fhir.bundle_helpers import create_bundle


@pytest.fixture
def empty_bundle():
    """Create an empty bundle for testing."""
    return create_bundle()


@pytest.fixture
def test_condition():
    """Create a test condition."""
    return create_condition(subject="Patient/123", code="123", display="Test Condition")


@pytest.fixture
def test_medication():
    """Create a test medication statement."""
    return create_medication_statement(
        subject="Patient/123", code="456", display="Test Medication"
    )


@pytest.fixture
def test_allergy():
    """Create a test allergy intolerance."""
    return create_allergy_intolerance(
        patient="Patient/123", code="789", display="Test Allergy"
    )
