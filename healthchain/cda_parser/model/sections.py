"""
https://wiki.ihe.net/index.php/1.3.6.1.4.1.19376.1.5.3.1.4.5
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union

from .datatypes import CD, CS, CE, II, IVL_TS


class PlayingEntity(BaseModel):
    classCode: str = Field("MMAT", alias="@classCode")
    code: Optional[CE] = None
    name: Optional[str] = None


class ParticipantRole(BaseModel):
    classCode: str = Field("MANU", alias="@classCode")
    playingEntity: Optional[PlayingEntity] = None


class Participant(BaseModel):
    typeCode: str = Field("CSM", alias="@typeCode")
    participantRole: Optional[ParticipantRole] = None


class Observation(BaseModel):
    classCode: str = Field("OBS", alias="@classCode")
    moodCode: str = Field("EVN", alias="@moodCode")
    templateId: Optional[Union[II, List[II]]] = None
    id: Optional[Union[II, List[II]]] = None
    code: CD
    text: Optional[Dict] = None
    value: Optional[Union[Dict, List[Dict]]] = None
    statusCode: Optional[CS] = None
    effectiveTime: Optional[IVL_TS] = None
    entryRelationship: Optional[Union[EntryRelationship, List[EntryRelationship]]] = (
        None
    )
    precondition: Optional[str] = None
    participant: Optional[Participant] = None


class EntryRelationship(BaseModel):
    typeCode: str = Field("SUBJ", alias="@typeCode")
    inversionInd: bool = Field(False, alias="@inversionInd")
    act: Optional[Act] = None
    observation: Optional[Observation] = None
    substanceAdministration: Optional[Dict] = None
    supply: Optional[Dict] = None


class Act(BaseModel):
    classCode: str = Field("ACT", alias="@classCode")
    moodCode: str = Field("EVN", alias="@moodCode")
    templateId: Optional[Union[II, List[II]]] = None
    id: Optional[Union[II, List[II]]] = None
    code: CD
    text: Optional[Dict] = None
    statusCode: Optional[CS] = None
    effectiveTime: Optional[IVL_TS] = None
    entryRelationship: Optional[Union[EntryRelationship, List[EntryRelationship]]] = (
        None
    )


class Entry(BaseModel):
    act: Optional[Act] = None
    substanceAdministration: Optional[Dict] = None


class Section(BaseModel):
    id: Optional[II] = None
    templateId: Optional[Union[II, List[II]]] = None
    code: Optional[CE] = None
    title: Optional[str] = None
    text: Optional[Dict] = None
    entry: Optional[Union[Entry, List[Entry]]] = None


# TODO: medication models - this is incomplete - better to parse it as a Dict and preserve all information
# than parsing it into a model with incomplete fields esp. with meds so leaving this here for now
# class SubstanceAdministration(BaseModel):
#     """
#     https://gazelle.ihe.net/CDAGenerator/cda/POCDMT000040SubstanceAdministration.html
#     """

#     classCode: str = "SBADM"
#     moodCode: str = "INT"
#     templateId: Optional[Union[II, List[II]]] = None
#     id: Optional[Union[II, List[II]]] = None
#     code: Optional[CD] = None
#     text: Optional[Dict] = None
#     statusCode: Optional[CS] = None
#     effectiveTime: Optional[Union[SXCM_TS, List[SXCM_TS]]] = None
#     routeCode: Optional[CE] = None
#     doseQuantity: Optional[IVL_PQ] = None
#     consumable: Consumable
#     entryRelationship: Optional[Union[EntryRelationship, List[EntryRelationship]]] = None
#     precondition: Optional[Union[Precondition, List[Precondition]]] = None
