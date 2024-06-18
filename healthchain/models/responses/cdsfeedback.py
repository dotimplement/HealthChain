"""
This is not compulsary

https://cds-hooks.org/specification/current/#feedback
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

from .cdsresponse import SimpleCoding


class OutcomeEnum(str, Enum):
    accepted = "accepted"
    overridden = "overridden"


class OverrideReason(BaseModel):
    reason: SimpleCoding
    userComment: Optional[str] = None


class CDSFeedback(BaseModel):
    """
    A feedback endpoint enables suggestion tracking & analytics.
    A CDS Service MAY support a feedback endpoint; a CDS Client SHOULD be capable of sending feedback.

    Attributes:
        card (str): The card.uuid from the CDS Hooks response. Uniquely identifies the card.
        outcome (str): The outcome of the action, either 'accepted' or 'overridden'.
        acceptedSuggestions (List[AcceptedSuggestion]): An array of accepted suggestions, required if the outcome is 'accepted'.
        overrideReason (Optional[OverrideReason]): The reason for overriding, including any coding and comments.
        outcomeTimestamp (datetime): The ISO8601 timestamp of when the action was taken on the card.

    Documentation: https://cds-hooks.org/specification/current/#feedback
    """

    card: str
    outcome: OutcomeEnum
    outcomeTimestamp: str
    acceptedSuggestion: Optional[Dict[str, Any]] = None
    overriddeReason: Optional[OverrideReason] = None
