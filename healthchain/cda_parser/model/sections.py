from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union


class Code(BaseModel):
    code: str = Field(None, alias="@code")
    codeSystem: str = Field(None, alias="@codeSystem")
    codeSystemName: str = Field(None, alias="@codeSystemName")
    displayName: str = Field(None, alias="@displayName")


class PlayingEntity(BaseModel):
    classCode: str = Field("MMAT", alias="@classCode")
    code: Optional[Code] = None
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
    templateId: Union[Dict, List[Dict]] = Field(default_factory=list)
    id: Union[Dict, List[Dict]] = Field(default_factory=list)
    code: Optional[Code] = None
    text: Optional[Dict] = None
    value: Union[Dict, List[Dict]] = Field(default_factory=list)
    statusCode: Optional[Dict] = None
    effectiveTime: Optional[Dict] = None
    entryRelationship: Union[EntryRelationship, List[EntryRelationship]] = Field(
        default_factory=list
    )
    precondition: Optional[str] = None
    participant: Optional[Participant] = None


class EntryRelationship(BaseModel):
    typeCode: str = Field("SUBJ", alias="@typeCode")
    inversionInd: bool = Field(False, alias="@inversionInd")
    act: Optional[Act] = None
    observation: Optional[Observation] = None
    substanceAdministration: Optional[str] = None
    supply: Optional[str] = None


class Act(BaseModel):
    classCode: str = Field("ACT", alias="@classCode")
    moodCode: str = Field("EVN", alias="@moodCode")
    templateId: Union[Dict, List[Dict]] = Field(default_factory=list)
    id: Union[Dict, List[Dict]] = Field(default_factory=list)
    code: Optional[Code] = None
    text: Optional[Dict] = None
    statusCode: Optional[Dict] = None
    effectiveTime: Optional[Dict] = None
    entryRelationship: Union[EntryRelationship, List[EntryRelationship]] = Field(
        default_factory=list
    )


class Entry(BaseModel):
    act: Optional[Act] = None
    # substanceAdministration: Optional[SubstanceAdministration] = None


class Section(BaseModel):
    id: Optional[Dict] = None
    templateId: Union[Dict, List[Dict]] = Field(default_factory=list)
    code: Optional[Code] = None
    title: Optional[str] = None
    text: Optional[Dict] = None
    entry: Union[Entry, List[Entry]] = Field(default_factory=list)
