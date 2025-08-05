"""
FHIR Error Handling for HealthChain Gateway.

This module provides standardized error handling for FHIR operations,
including status code mapping, error formatting, and exception types.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FHIRConnectionError(Exception):
    """Standardized FHIR connection error with state codes."""

    def __init__(
        self,
        message: str,
        code: str,
        state: Optional[str] = None,
        show_state: bool = True,
    ):
        """
        Initialize a FHIR connection error.

        Args:
            message: Human-readable error message e.g. Server does not allow client defined ids
            code: Error code or technical details e.g. METHOD_NOT_ALLOWED
            state: HTTP status code e.g. 405
            show_state: Whether to include the state in the error message
        """
        self.message = message
        self.code = code
        self.state = state
        if show_state:
            super().__init__(f"[{state} {code}] {message}")
        else:
            super().__init__(f"[{code}] {message}")


class FHIRErrorHandler:
    """
    Handles FHIR operation errors consistently across the gateway.

    Provides standardized error mapping, formatting, and exception handling
    for FHIR-specific operations and status codes.
    """

    # Map HTTP status codes to FHIR error types and messages
    # Based on: https://build.fhir.org/http.html
    ERROR_MAP = {
        400: "Resource could not be parsed or failed basic FHIR validation rules (or multiple matches were found for conditional criteria)",
        401: "Authorization is required for the interaction that was attempted",
        403: "You may not have permission to perform this operation",
        404: "The resource you are looking for does not exist, is not a resource type, or is not a FHIR end point",
        405: "The server does not allow client defined ids for resources",
        409: "Version conflict - update cannot be done",
        410: "The resource you are looking for is no longer available",
        412: "Version conflict - version id does not match",
        422: "Proposed resource violated applicable FHIR profiles or server business rules",
    }

    @classmethod
    def handle_fhir_error(
        cls,
        e: Exception,
        resource_type: str,
        fhir_id: Optional[str] = None,
        operation: str = "operation",
    ) -> None:
        """
        Handle FHIR operation errors consistently.

        Args:
            e: The original exception
            resource_type: The FHIR resource type being operated on
            fhir_id: The resource ID (if applicable)
            operation: The operation being performed

        Raises:
            FHIRConnectionError: Standardized FHIR error with proper formatting
        """
        error_msg = str(e)
        resource_ref = f"{resource_type}{'' if fhir_id is None else f'/{fhir_id}'}"

        # Try status code first
        status_code = getattr(e, "status_code", None)
        if status_code in cls.ERROR_MAP:
            msg = cls.ERROR_MAP[status_code]
            raise FHIRConnectionError(
                message=f"{operation} {resource_ref} failed: {msg}",
                code=error_msg,
                state=str(status_code),
                show_state=False,
            )

        # Fall back to message parsing
        error_msg_lower = error_msg.lower()
        for code, msg in cls.ERROR_MAP.items():
            if str(code) in error_msg_lower:
                raise FHIRConnectionError(
                    message=f"{operation} {resource_ref} failed: {msg}",
                    code=error_msg,
                    state=str(code),
                    show_state=False,
                )

        # Default fallback error
        raise FHIRConnectionError(
            message=f"{operation} {resource_ref} failed: HTTP error",
            code=error_msg,
            state=str(status_code) if status_code else "UNKNOWN",
            show_state=False,
        )

    @classmethod
    def create_validation_error(
        cls, message: str, resource_type: str = None, field_name: str = None
    ) -> FHIRConnectionError:
        """
        Create a standardized validation error.

        Args:
            message: The validation error message
            resource_type: The resource type being validated (optional)
            field_name: The specific field that failed validation (optional)

        Returns:
            FHIRConnectionError: Formatted validation error
        """
        if resource_type and field_name:
            formatted_message = (
                f"Validation failed for {resource_type}.{field_name}: {message}"
            )
        elif resource_type:
            formatted_message = f"Validation failed for {resource_type}: {message}"
        else:
            formatted_message = f"Validation failed: {message}"

        return FHIRConnectionError(
            message=formatted_message,
            code="VALIDATION_ERROR",
            state="422",  # Unprocessable Entity
        )

    @classmethod
    def create_connection_error(
        cls, message: str, source: str = None
    ) -> FHIRConnectionError:
        """
        Create a standardized connection error.

        Args:
            message: The connection error message
            source: The source name that failed to connect (optional)

        Returns:
            FHIRConnectionError: Formatted connection error
        """
        if source:
            formatted_message = f"Connection to source '{source}' failed: {message}"
        else:
            formatted_message = f"Connection failed: {message}"

        return FHIRConnectionError(
            message=formatted_message,
            code="CONNECTION_ERROR",
            state="503",  # Service Unavailable
        )

    @classmethod
    def create_authentication_error(
        cls, message: str, source: str = None
    ) -> FHIRConnectionError:
        """
        Create a standardized authentication error.

        Args:
            message: The authentication error message
            source: The source name that failed authentication (optional)

        Returns:
            FHIRConnectionError: Formatted authentication error
        """
        if source:
            formatted_message = f"Authentication to source '{source}' failed: {message}"
        else:
            formatted_message = f"Authentication failed: {message}"

        return FHIRConnectionError(
            message=formatted_message,
            code="AUTHENTICATION_ERROR",
            state="401",  # Unauthorized
        )
