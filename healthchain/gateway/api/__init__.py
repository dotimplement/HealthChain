"""
API module for the HealthChain Gateway.

This module provides API integration for healthcare systems including
FHIR, SOAP, CDS Hooks, and other healthcare interoperability standards.
"""

from .app import HealthChainAPI, create_app
from .router import FhirRouter

__all__ = ["HealthChainAPI", "create_app", "FhirRouter"]
