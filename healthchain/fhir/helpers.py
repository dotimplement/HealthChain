"""Convenience functions for creating minimal FHIR resources."""

from typing import Optional, List, Dict, Any
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding


def create_single_codeable_concept(
    code: str,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
) -> CodeableConcept:
    """Create a FHIR CodeableConcept with a single coding. Default system is SNOMED CT."""
    return CodeableConcept(coding=[Coding(system=system, code=code, display=display)])


def create_single_reaction(
    code: str,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
    severity: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Create a FHIR Reaction with a single coding. Default system is SNOMED CT."""
    return [
        {
            "manifestation": [
                CodeableConcept(
                    coding=[Coding(system=system, code=code, display=display)]
                )
            ],
            "severity": severity,
        }
    ]


def set_problem_list_item_category(condition: Condition) -> Condition:
    """Set the category of a FHIR Condition to problem-list-item."""
    condition.category = [
        create_single_codeable_concept(
            code="problem-list-item",
            display="Problem List Item",
            system="http://terminology.hl7.org/CodeSystem/condition-category",
        )
    ]
    return condition


def create_condition(
    subject: str,
    status: str = "active",
    code: Optional[str] = None,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
) -> Condition:
    """
    Create a minimal active FHIR Condition.
    If you need to create a more complex condition, use the FHIR Condition resource directly.
    https://build.fhir.org/condition.html

    Args:
        subject: REQUIRED. Reference to the patient (e.g. "Patient/123")
        status: REQUIRED. Clinical status (default: active)
        code: The condition code
        display: The display name for the condition
        system: The code system (default: SNOMED CT)
    """
    if code:
        condition_code = create_single_codeable_concept(code, display, system)
    else:
        condition_code = None

    condition = Condition(
        subject={"reference": subject},
        clinicalStatus=create_single_codeable_concept(
            code=status,
            display=status.capitalize(),
            system="http://terminology.hl7.org/CodeSystem/condition-clinical",
        ),
        code=condition_code,
    )

    return condition


def create_medication_statement(
    subject: str,
    status: Optional[str] = "recorded",
    code: Optional[str] = None,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
) -> MedicationStatement:
    """
    Create a minimal recorded FHIR MedicationStatement.
    If you need to create a more complex medication statement, use the FHIR MedicationStatement resource directly.
    https://build.fhir.org/medicationstatement.html

    Args:
        subject_reference: REQUIRED. Reference to the patient (e.g. "Patient/123")
        status: REQUIRED. Status of the medication (default: recorded)
        code: The medication code
        display: The display name for the medication
        system: The code system (default: SNOMED CT)
    """
    if code:
        medication_concept = create_single_codeable_concept(code, display, system)
    else:
        medication_concept = None

    medication = MedicationStatement(
        subject={"reference": subject},
        status=status,
        medication={"concept": medication_concept},
    )

    return medication


def create_allergy_intolerance(
    patient: str,
    code: Optional[str] = None,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
) -> AllergyIntolerance:
    """
    Create a minimal active FHIR AllergyIntolerance.
    If you need to create a more complex allergy intolerance, use the FHIR AllergyIntolerance resource directly.
    https://build.fhir.org/allergyintolerance.html

    Args:
        patient: REQUIRED. Reference to the patient (e.g. "Patient/123")
        code: The allergen code
        display: The display name for the allergen
        system: The code system (default: SNOMED CT)
    """
    if code:
        allergy_code = create_single_codeable_concept(code, display, system)
    else:
        allergy_code = None

    allergy = AllergyIntolerance(
        patient={"reference": patient},
        code=allergy_code,
    )

    return allergy
