"""
Protocol implementations for the HealthChain Gateway.

This module contains protocol-specific gateway implementations that provide
integration with various healthcare standards like FHIR, CDS Hooks, SOAP, etc.

These gateways handle the details of each protocol while presenting a consistent
interface for registration, event handling, and endpoint management.
"""

from .cdshooks import CDSHooksService
from .notereader import NoteReaderService
from .apiprotocol import ApiProtocol

__all__ = [
    "CDSHooksService",
    "NoteReaderService",
    "ApiProtocol",
]
