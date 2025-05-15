"""
Protocol implementations for the HealthChain Gateway.

This module contains protocol-specific gateway implementations that provide
integration with various healthcare standards like FHIR, CDS Hooks, SOAP, etc.

These gateways handle the details of each protocol while presenting a consistent
interface for registration, event handling, and endpoint management.
"""

from .fhirgateway import FHIRGateway
from .cdshooks import CDSHooksGateway
from .notereader import NoteReaderGateway
from .apiprotocol import ApiProtocol

__all__ = [
    "FHIRGateway",
    "CDSHooksGateway",
    "NoteReaderGateway",
    "ApiProtocol",
]
