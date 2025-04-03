import pytest

from pathlib import Path

from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance

from healthchain.interop.engine import InteropEngine


@pytest.fixture
def test_cda_xml():
    """Load test CDA XML file."""
    with open("tests/data/test_cda.xml", "r") as f:
        return f.read()


@pytest.fixture
def interop_engine():
    """Create an InteropEngine with actual configs."""
    project_root = Path(__file__).parent.parent.parent

    config_dir = project_root / "configs"

    if not config_dir.exists():
        pytest.skip(f"Config directory not found: {config_dir}")

    return InteropEngine(config_dir)


def test_cda_to_fhir_conversion(interop_engine, test_cda_xml):
    """Test CDA to FHIR conversion with real data.

    This test verifies that:
    - The engine successfully converts CDA to FHIR resources
    - The expected resource types (Condition, MedicationStatement, AllergyIntolerance) are present
    - The FHIR resources contain the correct data from the source CDA document
    """
    # Convert CDA to FHIR
    resources = interop_engine.to_fhir(test_cda_xml, "CDA")

    # Ensure resources are returned
    assert resources is not None
    assert len(resources) > 0

    # Check individual resources
    conditions = [r for r in resources if isinstance(r, Condition)]
    medications = [r for r in resources if isinstance(r, MedicationStatement)]
    allergies = [r for r in resources if isinstance(r, AllergyIntolerance)]

    assert len(conditions) > 0
    assert len(medications) > 0
    assert len(allergies) > 0

    # Verify specific data in the resources
    # Condition
    condition = conditions[0]
    assert "dev-" in condition.id
    assert condition.code.coding[0].code == "38341003"  # From test_cda.xml
    assert condition.code.coding[0].system == "http://snomed.info/sct"
    assert condition.subject.reference == "Patient/Foo"  # Default patient reference
    assert condition.clinicalStatus.coding[0].code == "active"
    assert (
        condition.clinicalStatus.coding[0].system
        == "http://terminology.hl7.org/CodeSystem/condition-clinical"
    )
    assert condition.clinicalStatus.coding[1].display == "Active"
    assert condition.clinicalStatus.coding[1].system == "http://snomed.info/sct"
    assert condition.clinicalStatus.coding[1].code == "55561003"
    assert condition.category[0].coding[0].code == "problem-list-item"
    assert condition.onsetDateTime  # need to fix datetime conversions first

    # Medication
    medication = medications[0]
    assert "dev-" in medication.id
    assert medication.status == "completed"
    assert medication.medication.concept.coding[0].code == "314076"
    assert (
        medication.medication.concept.coding[0].display
        == "lisinopril 10 MG Oral Tablet"
    )
    assert (
        medication.medication.concept.coding[0].system
        == "http://www.nlm.nih.gov/research/umls/rxnorm"
    )
    assert medication.subject.reference == "Patient/Foo"
    assert medication.dosage[0].timing.repeat.period == 0.5
    assert medication.dosage[0].timing.repeat.periodUnit == "d"
    assert (
        medication.dosage[0].route.coding[0].system
        == "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl"
    )
    assert medication.dosage[0].route.coding[0].display == "Oral"
    assert medication.dosage[0].route.coding[0].code == "C38288"
    assert medication.dosage[0].doseAndRate[0].doseQuantity.value == 30.0
    assert medication.dosage[0].doseAndRate[0].doseQuantity.unit == "mg"
    assert medication.effectivePeriod.end

    # Allergy
    allergy = allergies[0]
    assert "dev-" in allergy.id
    assert allergy.patient.reference == "Patient/Foo"
    assert allergy.clinicalStatus.coding[0].code == "active"
    assert (
        allergy.clinicalStatus.coding[0].system
        == "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical"
    )
    assert allergy.type.coding[0].code == "418471000"
    assert allergy.type.coding[0].display == "Propensity to adverse reactions to food"
    assert allergy.type.coding[0].system == "http://snomed.info/sct"
    assert allergy.code.coding[0].code == "102263004"
    assert allergy.code.coding[0].display == "EGGS"
    assert allergy.code.coding[0].system == "http://snomed.info/sct"
    assert allergy.reaction[0].manifestation[0].concept.coding[0].code == "65124004"
    assert allergy.reaction[0].manifestation[0].concept.coding[0].display == "Swelling"
    assert (
        allergy.reaction[0].manifestation[0].concept.coding[0].system
        == "http://snomed.info/sct"
    )
    assert allergy.reaction[0].severity == "severe"
    assert allergy.onsetDateTime


def test_fhir_to_cda_conversion(interop_engine, test_cda_xml):
    """Test FHIR to CDA conversion with real data.

    This test verifies that:
    - The engine successfully converts FHIR resources to a CDA document
    - The generated CDA contains the expected section types and structure
    - Key clinical information is preserved in the conversion
    """
    # First convert CDA to FHIR
    resources = interop_engine.to_fhir(test_cda_xml, "CDA")

    # Then convert back to CDA
    cda = interop_engine.from_fhir(resources, "CDA")

    # Ensure CDA document is returned
    assert cda is not None
    assert isinstance(cda, str)
    assert cda.startswith("<?xml version")
    assert "<ClinicalDocument" in cda

    # Check if the CDA contains expected sections
    assert "<section>" in cda

    # Check for common elements that should be in the CDA
    assert "Problem List" in cda
    assert "Medications" in cda
    assert "Allergies" in cda

    assert '<templateId root="2.16.840.1.113883.10.20.1.27"/>' in cda
    assert '<templateId root="1.3.6.1.4.1.19376.1.5.3.1.4.5.1"/>' in cda
    assert '<templateId root="2.16.840.1.113883.3.88.11.32.7"/>' in cda
    assert '<templateId root="2.16.840.1.113883.3.88.11.83.7"/>' in cda
    assert '<templateId root="1.3.6.1.4.1.19376.1.5.3.1.4.5"/>' in cda
    assert '<templateId root="2.16.840.1.113883.10.20.1.28"/>' in cda

    assert 'code="38341003" codeSystem="2.16.840.1.113883.6.96"' in cda
    assert 'code="55561003" codeSystem="2.16.840.1.113883.6.96"' in cda
    assert '<period unit="d" value="0.5"/>' in cda
    assert (
        '<routeCode code="C38288" codeSystem="2.16.840.1.113883.3.26.1.1" displayName="Oral"/>'
        in cda
    )
    assert '<doseQuantity unit="mg" value="30.0"/>' in cda
    assert (
        'code="314076" codeSystem="2.16.840.1.113883.6.88" displayName="lisinopril 10 MG Oral Tablet"'
        in cda
    )
    assert (
        '<value xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" code="755561003" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT" xsi:type="CE" displayName="Active"/>'
        in cda
    )
    assert (
        '<code code="418471000" codeSystem="2.16.840.1.113883.6.96" displayName="Propensity to adverse reactions to food"/>'
        in cda
    )

    assert (
        'code="102263004" codeSystem="2.16.840.1.113883.6.96" displayName="EGGS"' in cda
    )
    assert (
        'code="65124004" codeSystem="2.16.840.1.113883.6.96" displayName="Swelling"'
        in cda
    )
    assert (
        '<code code="SEV" codeSystem="2.16.840.1.113883.5.4" codeSystemName="ActCode" displayName="Severity"/>'
        in cda
    )
    assert (
        'code="H" codeSystem="2.16.840.1.113883.5.1063" codeSystemName="SeverityObservation" displayName="H"'
        in cda
    )


def test_round_trip_equivalence(interop_engine, test_cda_xml):
    """Test that converting CDA to FHIR and back preserves essential information."""
    # First conversion: CDA -> FHIR
    resources = interop_engine.to_fhir(test_cda_xml, "CDA")

    # Get resource types from original resources
    original_resource_types = {r.__class__.__name__ for r in resources}

    # Second conversion: FHIR -> CDA
    cda_result = interop_engine.from_fhir(resources, "CDA")

    # Third conversion: CDA -> FHIR (to check equivalence)
    resources_result = interop_engine.to_fhir(cda_result, "CDA")

    # Get resource types from result resources
    result_resource_types = {r.__class__.__name__ for r in resources_result}

    assert original_resource_types == result_resource_types

    # Get conditions and medication statements from both resource sets
    original_conditions = [r for r in resources if isinstance(r, Condition)]
    result_conditions = [r for r in resources_result if isinstance(r, Condition)]

    original_medications = [r for r in resources if isinstance(r, MedicationStatement)]
    result_medications = [
        r for r in resources_result if isinstance(r, MedicationStatement)
    ]

    # Compare the first condition and medication statement
    assert (
        result_conditions[0].code.coding[0].code
        == original_conditions[0].code.coding[0].code
    )
    assert (
        result_medications[0].medication.concept.coding[0].code
        == original_medications[0].medication.concept.coding[0].code
    )

    # TODO: allergy intolerance reverse parsing isn't quite right look into this
    # print(resources_result[2].model_dump_json(indent=2))
    # print(resources[2].model_dump_json(indent=2))
    # assert resources_result[2].code.coding[0].code == resources[2].code.coding[0].code
