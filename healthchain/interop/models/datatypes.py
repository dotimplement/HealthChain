"""
Contains CDA datatype objects with pydantic validation
https://gazelle.ihe.net/CDAGenerator/datatypes/datatypes.html
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Union


class ANY(BaseModel):
    nullFlavor: Optional[str] = Field(default=None, alias="@nullFlavor")


class BIN(ANY):
    """
    Binary data.
    """

    mixed: Optional[Dict] = None
    representation: Optional[str] = Field(
        default=None, alias="@representation"
    )  # enumeration B64 or TXT


class URL(ANY):
    """
    URL data.
    """

    value: Optional[str] = Field(default=None, alias="@value")


class TEL(URL):
    """
    A telephone number, e-mail address, or other locator for a resource mediated
    by telecommunication equipment. The address is specified as a URL qualified
    by time specification and use codes that help in deciding which address to
    use for a given time and purpose.
    """

    usablePeriod: Optional[Union[SXCM_TS, List[SXCM_TS]]] = None
    use: Optional[Union[str, List[str]]] = Field(default=None, alias="@use")


class ED(BIN):
    """
    Data that is primarily intended for human interpretation or for
    further machine processing is outside the scope of HL7.
    """

    reference: Optional[TEL] = None
    thumbnail: Optional[ED] = None  # thumbnail
    compression: Optional[str] = Field(
        default=None,
        alias="@compression",
        description="Indicates whether the raw byte data is compressed, and what compression algorithm was used.",
    )  # enum
    integrityCheck: Optional[str] = Field(default=None, alias="@integrityCheck")
    integrityCheckAlgorithm: Optional[str] = Field(
        default=None, alias="@integrityCheckAlgorithm"
    )  # enum SHA1 or SHA256
    language: Optional[str] = Field(default=None, alias="@language")
    mediaType: Optional[str] = Field(default=None, alias="@mediaType")


class QTY(ANY):
    """
    The quantity data type is an abstract generalization for all data
    types (1) whose value set has an order relation (less-or-equal)
    and (2) where difference is defined in all of the data type's
    totally ordered value subsets. The quantity type abstraction is
    needed in defining certain other types, such as the interval and
    the probability distribution.
    """

    pass


class II(ANY):
    """
    An identifier that uniquely identifies a thing or object.
    """

    assigningAuthorityName: Optional[str] = Field(
        default=None, alias="@assigningAuthorityName"
    )
    displayable: Optional[bool] = Field(default=None, alias="@displayable")
    extension: Optional[str] = Field(default=None, alias="@extension")
    root: Optional[str] = Field(default=None, alias="@root")


class CD(ANY):
    """
    A concept descriptor represents any kind of concept usually by giving a
    code defined in a code system. A concept descriptor can contain the
    original text or phrase that served as the basis of the coding and one
    or more translations into different coding systems.
    """

    originalText: Optional[Union[str, Dict]] = (
        None  # parse as dict or str for more flexibility
    )
    qualifier: Optional[Union[str, List[str]]] = None  # CR
    translation: Optional[Union[CD, List[CD]]] = Field(default=None)
    code: Optional[str] = Field(default=None, alias="@code")
    codeSystem: Optional[str] = Field(default=None, alias="@codeSystem")
    codeSystemName: Optional[str] = Field(default=None, alias="@codeSystemName")
    codeSystemVersion: Optional[str] = Field(default=None, alias="@codeSystemVersion")
    displayName: Optional[str] = Field(default=None, alias="@displayName")


class CE(CD):
    """
    Coded data, consists of a coded value (CV) and, optionally,
    coded value(s) from other coding systems that identify the same
    concept. Used when alternative codes may exist.
    """

    pass


class CV(CE):
    """
    Coded data, consists of a code, display name, code system,
    and original text. Used when a single code value must be sent.
    """

    pass


class CS(CV):
    """
    Coded data, consists of a code, display name, code system,
    and original text. Used when a single code value must be sent.
    """

    pass


class PQR(CV):
    """
    A representation of a physical quantity in a unit from any code
    system. Used to show alternative representation for a physical
    quantity.
    """

    value: Optional[float] = Field(default=None, alias="@value")


class TS(QTY):
    """
    A quantity specifying a point on the axis of natural time. A point
    in time is most often represented as a calendar expression.
    """

    value: Optional[str] = Field(default=None, alias="@value")


class PQ(QTY):
    """
    A dimensioned quantity expressing the result of a measurement act.
    """

    translation: Optional[Union[PQR, List[PQR]]] = Field(
        default=None,
        description="An alternative representation of the same physical quantity expressed in a different unit, of a different unit code system and possibly with a different value.",
    )
    unit: Optional[str] = Field(
        default=None,
        alias="@unit",
        description="The unit of measure specified in the Unified Code for Units of Measure (UCUM) [http://aurora.rg.iupui.edu/UCUM].",
    )
    value: Optional[float] = Field(
        default=None,
        alias="@value",
        description="The magnitude of the quantity measured in terms of the unit.",
    )


class SXCM_TS(TS):
    operator: Optional[str] = Field(default=None, alias="@operator")  # enumeration


class SXCM_PQ(PQ):
    operator: Optional[str] = Field(default=None, alias="@operator")  # enumeration


class IVXB_TS(TS):
    inclusive: Optional[bool] = Field(
        None,
        alias="@inclusive",
        description="Specifies whether the limit is included in the interval.",
    )


class IVXB_PQ(PQ):
    inclusive: Optional[bool] = Field(
        None,
        alias="@inclusive",
        description="Specifies whether the limit is included in the interval.",
    )


class IVL_PQ(SXCM_PQ):
    low: Optional[IVXB_PQ] = Field(
        default=None, description="The low limit of the interval."
    )
    center: Optional[PQ] = Field(
        default=None,
        description="The arithmetic mean of the interval (low plus high divided by 2). The purpose of distinguishing the center as a semantic property is for conversions of intervals from and to point values.",
    )
    width: Optional[PQ] = Field(
        default=None,
        description="The difference between high and low boundary. The purpose of distinguishing a width property is to handle all cases of incomplete information symmetrically. In any interval representation only two of the three properties high, low, and width need to be stated and the third can be derived.",
    )
    high: Optional[IVXB_PQ] = Field(
        default=None, description="The high limit of the interval."
    )


class IVL_TS(SXCM_TS):
    """
    Time interval
    """

    low: Optional[IVXB_TS] = Field(
        default=None, description="The low limit of the interval."
    )
    center: Optional[TS] = Field(
        default=None,
        description="The arithmetic mean of the interval (low plus high divided by 2). The purpose of distinguishing the center as a semantic property is for conversions of intervals from and to point values.",
    )
    width: Optional[PQ] = Field(
        default=None,
        description="The difference between high and low boundary. The purpose of distinguishing a width property is to handle all cases of incomplete information symmetrically. In any interval representation only two of the three properties high, low, and width need to be stated and the third can be derived.",
    )
    high: Optional[IVXB_TS] = Field(
        default=None, description="The high limit of the interval."
    )


class PIVL_TS(SXCM_TS):
    phase: Optional[IVL_TS] = Field(
        default=None,
        description="A prototype of the repeating interval specifying the duration of each occurrence and anchors the periodic interval sequence at a certain point in time.",
    )
    period: Optional[PQ] = Field(
        default=None,
        description="A time duration specifying a reciprocal measure of the frequency at which the periodic interval repeats.",
    )
    alignment: Optional[CalendarCycle] = Field(
        default=None,
        alias="@alignment",
        description="Specifies if and how the repetitions are aligned to the cycles of the underlying calendar (e.g., to distinguish every 30 days from 'the 5th of every month'.) A non-aligned periodic interval recurs independently from the calendar. An aligned periodic interval is synchronized with the calendar.",
    )
    institutionSpecified: Optional[bool] = Field(
        default=None,
        alias="@institutionSpecified",
        description="Indicates whether the exact timing is up to the party executing the schedule (e.g., to distinguish 'every 8 hours' from '3 times a day'.)",
    )


class CalendarCycle(ANY):
    name: Optional[str] = None  # enum


CD.model_rebuild()
