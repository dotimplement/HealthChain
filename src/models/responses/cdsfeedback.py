"""
This is not compulsary

https://cds-hooks.org/specification/current/#feedback
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

from .cdsservice import Coding


class OutcomeEnum(str, Enum):
    accepted = "accepted"
    overridden = "overridden"


class OverrideReason(BaseModel):
    reason: Coding
    userComment: Optional[str] = None


class CDSFeedback(BaseModel):
    """
    https://cds-hooks.org/specification/current/#feedback
    """

    card: str
    outcome: OutcomeEnum
    outcomeTimestamp: str
    acceptedSuggestion: Optional[Dict[str, Any]] = None
    overriddeReason: Optional[OverrideReason] = None
