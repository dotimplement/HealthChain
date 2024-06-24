"""
Contains CDA datatype objects with pydantic validation
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


# TODO: need to give them aliases, only keep ones you need


class ANY(BaseModel):
    resource_type: str = Field(
        "Any", description="This field provides a description for each date type"
    )
    nullFlavor: Optional[str] = Field(default=None, alias="@nullFalvor")


class BIN(ANY):
    resource_type: str = Field("BIN", description="Binary data.")
    mixed: Optional[Dict] = None
    representation: Optional[str] = None  # enumeration B64 or TXT


class URL(ANY):
    resource_type: str = Field("URL", description="URL data.")
    value: Optional[str] = None


class TEL(URL):
    resource_type: str = Field(
        "TEL",
        description="A telephone number, e-mail address, or other "
        "locator for a resource mediated by telecommunication equipment. "
        "The address is specified as a URL qualified by time specification "
        "and use codes that help in deciding which address to use for a "
        "given time and purpose.",
    )
    usablePeriod: Optional[List[SXCM_TS]] = None
    use: Optional[List[str]] = None


class ED(BIN):
    resource_type: str = Field(
        "ED",
        description="Data that is primarily intended for human interpretation or for "
        "further machine processing is outside the scope of HL7.",
    )
    reference: Optional[TEL] = None
    thumbnail: Optional[str] = None  # thumbnail
    compression: Optional[str] = None  # enum
    integrityCheck: Optional[str] = None
    integrityCheckAlgorithm: Optional[str] = None  # enum SHA1 or SHA256
    language: Optional[str] = None
    mediaType: Optional[str] = None


class QTY(ANY):
    resource_type: str = Field(
        "QTY",
        description="The quantity data type is an abstract generalization for all data "
        "types (1) whose value set has an order relation (less-or-equal) "
        "and (2) where difference is defined in all of the data type's "
        "totally ordered value subsets. The quantity type abstraction is "
        "needed in defining certain other types, such as the interval and "
        "the probability distribution.",
    )


class II(ANY):
    resource_type: str = Field(
        "II", description="An identifier that uniquely identifies a thing or object."
    )
    assigningAuthorityName: Optional[str] = Field(
        default=None, alias="@assigningAuthorityName"
    )
    displayable: Optional[bool] = Field(default=None, alias="@displayable")
    extension: Optional[str] = Field(default=None, alias="@extension")
    root: Optional[str] = Field(default=None, alias="@root")


class CD(ANY):
    resource_type: str = Field(
        "CD",
        description="A concept descriptor represents any kind of concept usually by giving a "
        "code defined in a code system. A concept descriptor can contain the "
        "original text or phrase that served as the basis of the coding and one "
        "or more translations into different coding systems.",
    )
    originalText: Optional[ED] = None
    qualifier: Optional[List[str]] = None  # CR
    translation: Optional[List[CD]] = Field(default_factory=list)
    code: Optional[str] = Field(default=None, alias="@code")
    codeSystem: Optional[str] = Field(default=None, alias="@codeSystem")
    codeSystemName: Optional[str] = Field(default=None, alias="@codeSystemName")
    displayName: Optional[str] = Field(default=None, alias="@displayName")


CD.model_rebuild()


class CE(CD):
    resource_type: str = Field(
        "CE",
        description="Coded data, consists of a coded value (CV) and, optionally, "
        "coded value(s) from other coding systems that identify the same "
        "concept. Used when alternative codes may exist.",
    )


class CV(CE):
    resource_type: str = Field(
        "CV",
        description="Coded data, consists of a code, display name, code system, "
        "and original text. Used when a single code value must be sent.",
    )


class PQR(CV):
    resource_type: str = Field(
        "PQR",
        description="A representation of a physical quantity in a unit from any code "
        "system. Used to show alternative representation for a physical "
        "quantity.",
    )
    value: Optional[float] = None


class CS(CV):
    resource_type: str = Field(
        "CS",
        description="Coded data, consists of a code, display name, code system, and original "
        "text. Used when a single code value must be sent.",
    )


class PQ(QTY):
    resource_type: str = Field(
        "PQ",
        description="A dimensioned quantity expressing the result of a measurement act.",
    )
    translation: Optional[List[PQR]] = None
    unit: Optional[str] = None
    value: Optional[float] = None


class TS(QTY):
    resource_type: str = Field(
        "TS",
        description="A quantity specifying a point on the axis of natural time. A point "
        "in time is most often represented as a calendar expression.",
    )
    value: Optional[str] = None


class SXCM_TS(TS):
    resource_type: str = Field("SXCM_TS", description="")
    operator: Optional[str] = None  # enumeration


class SXCM_PQ(PQ):
    resource_type: str = Field("SXCM_PQ", description="")
    operator: Optional[str] = None  # enumeration


class IVXB_TS(SXCM_TS):
    resource_type: str = Field("IVXB_TS", description="")
    inclusive: Optional[bool] = Field(
        None, description="Specifies whether the limit is included in the interval."
    )


class IVXB_PQ(PQ):
    resource_type: str = Field("IVXB_PQ", description="")
    inclusive: Optional[bool] = Field(
        None, description="Specifies whether the limit is included in the interval."
    )


class IVL_PQ(SXCM_PQ):
    resource_type: str = Field("IVL_PQ", description="")
    low: Optional[IVXB_PQ] = None
    center: Optional[PQ] = None
    width: Optional[PQ] = None
    high: Optional[IVXB_PQ] = None


class IVL_TS(IVXB_TS):
    resource_type: str = Field("IVL_TS", description="Time interval.")
    low: Optional[IVXB_TS] = None
    center: Optional[TS] = None
    width: Optional[PQ] = None
    high: Optional[IVXB_TS] = None


class PIVL_TS(SXCM_TS):
    resource_type: str = Field("PIVL_TS", description="")
    phase: Optional[IVL_TS] = None
    period: Optional[PQ] = None
    alignment: Optional[CalendarCycle] = None
    institutionSpecified: Optional[bool] = False


class CalendarCycle(ANY):
    resource_type: str = Field("CalendarCycle", description="")
    name: Optional[str] = None
