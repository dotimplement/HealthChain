from pydantic import BaseModel
from typing import Optional


class Concept(BaseModel):
    """
    A more lenient, system agnostic representation of a concept e.g. problems, medications, allergies
    that can be converted to CDA or FHIR
    """

    code: Optional[str] = None
    code_system: Optional[str] = None
    code_system_name: Optional[str] = None
    display_name: Optional[str] = None
    status: Optional[str] = None
    recorded_date: Optional[str] = None


class ProblemConcept(Concept):
    """
    Contains problem/condition specific fields
    """

    onset_date: Optional[str] = None
    abatement_date: Optional[str] = None


class MedicationConcept(Concept):
    """
    Contains medication specific fields
    """

    dosage: Optional[str] = None
    precondition: Optional[str] = None


class AllergyConcept(Concept):
    """
    Contains allergy specific fields
    """

    allergy_type: Optional[str] = None
    severity: Optional[str] = None
    reaction: Optional[str] = None
