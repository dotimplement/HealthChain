from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from .sections import Section


class Component(BaseModel):
    section: Optional[Section] = None
    structuredBody: Optional[StructuredBody] = None


class StructuredBody(BaseModel):
    component: List[Component]


class CDA(BaseModel):
    xmlns: str = Field("urn:hl7-org:v3", alias="@xmlns")
    realmCode: Dict
    typeId: Dict
    templateId: List[Dict]
    id: Dict
    code: Dict
    title: str
    effectiveTime: Dict
    confidentialityCode: Dict
    languageCode: Dict
    component: Component
