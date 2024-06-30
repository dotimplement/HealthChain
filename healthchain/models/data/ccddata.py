from pydantic import BaseModel

from typing import Optional, List, Union, Dict

from healthchain.models.data.concept import (
    ProblemConcept,
    MedicationConcept,
    AllergyConcept,
)


class CcdData(BaseModel):
    """
    Data model for CCD (Continuity of Care Document) that can be converted to CDA.
    Data is stored as FHIR.
    """

    problems: Optional[List[ProblemConcept]] = None
    allergies: Optional[List[AllergyConcept]] = None
    medications: Optional[List[MedicationConcept]] = None
    note: Optional[Union[Dict, str]] = None
    cda_xml: Optional[str] = None
