from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, model_validator
from typing import Optional, List, Dict
from typing_extensions import Self


class IndicatorEnum(str, Enum):
    """
    Urgency/importance of what Card conveys.
    Allowed values, in order of increasing urgency, are: info, warning, critical.
    The CDS Client MAY use this field to help make UI display decisions such as sort order or coloring.
    """

    info = "info"
    warning = "warning"
    critical = "critical"


class SelectionBehaviorEnum(str, Enum):
    """
    Describes the intended selection behavior of the suggestions in the card.
    Allowed values are: at-most-one, indicating that the user may choose none or
    at most one of the suggestions; any, indicating that the end user may choose
    any number of suggestions including none of them and all of them.
    CDS Clients that do not understand the value MUST treat the card as an error.
    """

    at_most_one = "at-most-one"
    any = "any"


class ActionTypeEnum(str, Enum):
    """
    The type of action being performed
    """

    create = "create"
    update = "update"
    delete = "delete"


class LinkTypeEnum(str, Enum):
    """
    The type of the given URL. There are two possible values for this field.
    A type of absolute indicates that the URL is absolute and should be treated as-is.
    A type of smart indicates that the URL is a SMART app launch URL and the CDS Client
    should ensure the SMART app launch URL is populated with the appropriate SMART
    launch parameters.
    """

    absolute = "absolute"
    smart = "smart"


class Link(BaseModel):
    """
    * CDS Client support for appContext requires additional coordination with the authorization
    server that is not described or specified in CDS Hooks nor SMART.

    * Autolaunchable is experimental

    https://cds-hooks.org/specification/current/#link
    """

    label: str
    url: HttpUrl
    type: LinkTypeEnum
    appContext: Optional[str] = None
    autoLaunchable: Optional[bool]

    @model_validator(mode="after")
    def validate_link(self) -> Self:
        if self.appContext:
            assert (
                self.type == LinkTypeEnum.smart
            ), "'type' must be 'smart' for appContext to be valued."

        return self


class SimpleCoding(BaseModel):
    """
    The Coding data type captures the concept of a code. This coding type is a standalone data type
    in CDS Hooks modeled after a trimmed down version of the FHIR Coding data type.
    """

    code: str
    system: str
    display: Optional[str] = None


class Action(BaseModel):
    """
    Within a suggestion, all actions are logically AND'd together, such that a user selecting a
    suggestion selects all of the actions within it. When a suggestion contains multiple actions,
    the actions SHOULD be processed as per FHIR's rules for processing transactions with the CDS
    Client's fhirServer as the base url for the inferred full URL of the transaction bundle entries.

    https://cds-hooks.org/specification/current/#action
    """

    type: ActionTypeEnum
    description: str
    resource: Optional[Dict] = None
    resourceId: Optional[str] = None

    @model_validator(mode="after")
    def validate_action_type(self) -> Self:
        if self.type in [ActionTypeEnum.create, ActionTypeEnum.update]:
            assert (
                self.resource
            ), f"'resource' must be provided when type is '{self.type.value}'"
        else:
            assert (
                self.resourceId
            ), f"'resourceId' must be provided when type is '{self.type.value}'"

        return self


class Suggestion(BaseModel):
    """
    Allows a service to suggest a set of changes in the context of the current activity
    (e.g. changing the dose of a medication currently being prescribed, for the order-sign activity).
    If suggestions are present, selectionBehavior MUST also be provided.

    https://cds-hooks.org/specification/current/#suggestion
    """

    label: str
    uuid: Optional[str] = None
    isRecommended: Optional[bool]
    actions: Optional[List[Action]] = []


class Source(BaseModel):
    """
    Grouping structure for the Source of the information displayed on this card.
    The source should be the primary source of guidance for the decision support Card represents.

    https://cds-hooks.org/specification/current/#source
    """

    label: str
    url: Optional[HttpUrl] = None
    icon: Optional[HttpUrl] = None
    topic: Optional[SimpleCoding] = None


class Card(BaseModel):
    """
    Cards can provide a combination of information (for reading), suggested actions
    (to be applied if a user selects them), and links (to launch an app if the user selects them).
    The CDS Client decides how to display cards, but this specification recommends displaying suggestions
    using buttons, and links using underlined text.

    https://cds-hooks.org/specification/current/#card-attributes
    """

    summary: str = Field(..., max_length=140)
    indicator: IndicatorEnum
    source: Source
    uuid: Optional[str] = None
    detail: Optional[str] = None
    suggestions: Optional[List[Suggestion]] = None
    selectionBehavior: Optional[SelectionBehaviorEnum] = None
    overrideReasons: Optional[List[SimpleCoding]] = None
    links: Optional[List[Link]] = None

    @model_validator(mode="after")
    def validate_suggestions(self) -> Self:
        if self.suggestions is not None:
            assert self.selectionBehavior, f"'selectionBehavior' must be given if 'suggestions' is present! Choose from {[v for v in SelectionBehaviorEnum.value]}"
        return self


class CDSResponse(BaseModel):
    """
    Http response
    """

    cards: List[Card] = []
    systemActions: Optional[Action] = None
