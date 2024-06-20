from pydantic import BaseModel

from typing import Dict, Optional

from healthchain.fhir_resources.condition import Condition
from healthchain.fhir_resources.medicationadministration import MedicationAdministration
from healthchain.fhir_resources.documentreference import DocumentReference


class CcdData(BaseModel):
    """
    Data model for CCD (Continuity of Care Document) that can be converted to CDA.
    Data is stored as FHIR.
    """

    problems: Optional[Condition] = None
    allergies: Optional[Dict] = None  # TODO: IMPLEMENT ALLERGIES
    medications: Optional[MedicationAdministration] = (
        None  # TODO: IMPLEMENT MEDICATIONSTATEMENT
    )
    note: Optional[DocumentReference] = None
    cda_xml: Optional[str] = None
