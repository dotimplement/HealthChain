from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Union


class Standard(Enum):
    cda = "cda"
    fhir = "fhir"


class DataType(BaseModel):
    """
    Base class for all data types
    """

    _source: Optional[Dict] = None


class Quantity(DataType):
    # TODO: validate conversions str <-> float
    value: Optional[Union[str, float]] = None
    unit: Optional[str] = None


class Range(DataType):
    low: Optional[Quantity] = None
    high: Optional[Quantity] = None


class TimeInterval(DataType):
    period: Optional[Quantity] = None
    phase: Optional[Range] = None
    institution_specified: Optional[bool] = None


class Concept(BaseModel):
    """
    A more lenient, system agnostic representation of a concept e.g. problems, medications, allergies
    that can be converted to CDA or FHIR
    """

    _standard: Optional[Standard] = None
    code: Optional[str] = None
    code_system: Optional[str] = None
    code_system_name: Optional[str] = None
    display_name: Optional[str] = None


class ProblemConcept(Concept):
    """
    Contains problem/condition specific fields
    """

    onset_date: Optional[str] = None
    abatement_date: Optional[str] = None
    status: Optional[str] = None
    recorded_date: Optional[str] = None


class MedicationConcept(Concept):
    """
    Contains medication specific fields
    """

    dosage: Optional[Quantity] = None
    route: Optional[Concept] = None
    frequency: Optional[TimeInterval] = None
    duration: Optional[Range] = None
    precondition: Optional[Dict] = None


class AllergyConcept(Concept):
    """
    Contains allergy specific fields

    Defaults allergy type to propensity to adverse reactions in SNOMED CT
    """

    allergy_type: Optional[Concept] = Field(
        default=Concept(
            code="420134006",
            code_system="2.16.840.1.113883.6.96",
            code_system_name="SNOMED CT",
            display_name="Propensity to adverse reactions",
        )
    )
    severity: Optional[Concept] = None
    reaction: Optional[Concept] = None
