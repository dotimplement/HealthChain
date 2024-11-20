from pydantic import BaseModel
from typing import Optional, Union, Dict

from healthchain.models.data.concept import ConceptLists


class CcdData(BaseModel):
    """
    Data model for CCD (Continuity of Care Document) that can be converted to CDA.

    Attributes:
        concepts (ConceptLists): Container for medical concepts (problems, allergies, medications)
            extracted from the document. Defaults to empty ConceptLists.
        note (Optional[Union[Dict, str]]): The clinical note text, either as a string or
            dictionary of sections. Defaults to None.
        cda_xml (Optional[str]): The raw CDA XML string representation of the document.
            Defaults to None.
    """

    concepts: ConceptLists = ConceptLists()
    note: Optional[Union[Dict, str]] = None
    cda_xml: Optional[str] = None
