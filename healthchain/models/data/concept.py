from enum import Enum
from pydantic import BaseModel
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

    dosage: Optional[Union[Range, Quantity]] = None
    route: Optional[Concept] = None
    frequency: Optional[TimeInterval] = None
    duration: Optional[Range] = None
    precondition: Optional[Dict] = None


class AllergyConcept(Concept):
    """
    Contains allergy specific fields
    """

    allergy_type: Optional[str] = None
    severity: Optional[str] = None
    reaction: Optional[str] = None
