from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union

from healthchain.cda_parser.model.datatypes import CE, CS, II, TS

from .sections import Section


class Component2(BaseModel):
    """
    https://gazelle.ihe.net/CDAGenerator/cda/POCDMT000040Component2.html
    """

    structuredBody: Optional[StructuredBody] = None


class Component3(BaseModel):
    """
    https://gazelle.ihe.net/CDAGenerator/cda/POCDMT000040Component3.html
    """

    section: Section


class StructuredBody(BaseModel):
    """
    https://gazelle.ihe.net/CDAGenerator/cda/POCDMT000040StructuredBody.html
    """

    component: List[Component3]


class ClinicalDocument(BaseModel):
    """
    https://gazelle.ihe.net/CDAGenerator/cda/POCDMT000040ClinicalDocument.html
    """

    xmlns: str = Field("urn:hl7-org:v3", alias="@xmlns")
    realmCode: Optional[CS] = None
    typeId: Dict
    templateId: Optional[Union[II, List[II]]] = None
    id: II
    code: CE
    title: Optional[str] = None
    effectiveTime: TS
    confidentialityCode: CE
    languageCode: Optional[CS]
    component: Component2
