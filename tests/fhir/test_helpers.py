from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.codeableconcept import CodeableConcept


from healthchain.fhir.helpers import (
    create_single_codeable_concept,
    create_single_reaction,
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
    set_problem_list_item_category,
)


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
    assert isinstance(reaction[0]["manifestation"][0], CodeableConcept)
    assert reaction[0]["manifestation"][0].coding[0].code == "123"
    assert reaction[0]["manifestation"][0].coding[0].display == "Test Reaction"
    assert reaction[0]["manifestation"][0].coding[0].system == "http://test.system"


def test_create_condition():
    """Test creating a condition with all optional fields."""
    condition = create_condition(
        subject="Patient/123",
        status="resolved",
        code="123",
        display="Test Condition",
        system="http://test.system",
    )

    assert isinstance(condition, Condition)
    assert condition.subject.reference == "Patient/123"
    assert condition.clinicalStatus.coding[0].code == "resolved"
    assert condition.code.coding[0].code == "123"
    assert condition.code.coding[0].display == "Test Condition"
    assert condition.code.coding[0].system == "http://test.system"

    set_problem_list_item_category(condition)
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
    assert allergy.patient.reference == "Patient/123"
    assert allergy.code.coding[0].code == "123"
    assert allergy.code.coding[0].display == "Test Allergy"
    assert allergy.code.coding[0].system == "http://test.system"
