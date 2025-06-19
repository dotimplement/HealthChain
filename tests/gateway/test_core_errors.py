"""
Tests for the FHIR error handling module in the HealthChain gateway system.

This module tests standardized error handling for FHIR operations:
- FHIRConnectionError creation and formatting
- FHIRErrorHandler status code mapping and error processing
"""

import pytest
from unittest.mock import Mock

from healthchain.gateway.core.errors import (
    FHIRConnectionError,
    FHIRErrorHandler,
)


@pytest.mark.parametrize(
    "init_args,expected_message",
    [
        # With state displayed
        (
            {
                "message": "Resource not found",
                "code": "NOT_FOUND",
                "state": "404",
                "show_state": True,
            },
            "[404 NOT_FOUND] Resource not found",
        ),
        # Without state displayed
        (
            {
                "message": "Authentication failed",
                "code": "UNAUTHORIZED",
                "state": "401",
                "show_state": False,
            },
            "[UNAUTHORIZED] Authentication failed",
        ),
        # No state provided
        (
            {
                "message": "Generic error",
                "code": "GENERIC_ERROR",
                "state": None,
                "show_state": True,
            },
            "[None GENERIC_ERROR] Generic error",
        ),
    ],
)
def test_fhir_connection_error_message_formatting(init_args, expected_message):
    """FHIRConnectionError formats error messages correctly based on configuration."""
    error = FHIRConnectionError(**init_args)

    assert str(error) == expected_message
    assert error.message == init_args["message"]
    assert error.code == init_args["code"]
    assert error.state == init_args["state"]


@pytest.mark.parametrize(
    "status_code,expected_message_content",
    [
        (400, "Resource could not be parsed or failed basic FHIR validation rules"),
        (401, "Authorization is required for the interaction that was attempted"),
        (404, "The resource you are looking for does not exist"),
    ],
)
def test_fhir_error_handler_status_code_mapping(status_code, expected_message_content):
    """FHIRErrorHandler maps HTTP status codes to appropriate FHIR error messages."""
    mock_exception = Mock()
    mock_exception.status_code = status_code

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(mock_exception, "Patient", "123", "read")

    error = exc_info.value
    assert expected_message_content in error.message
    assert "read Patient/123 failed" in error.message
    assert error.state == str(status_code)


@pytest.mark.parametrize(
    "resource_type,fhir_id,operation,expected_resource_ref",
    [
        # With ID
        ("Patient", "123", "read", "Patient/123"),
        # Without ID (e.g., search operations)
        ("Observation", None, "search", "Observation"),
        # Complex resource type
        ("DiagnosticReport", "report-456", "update", "DiagnosticReport/report-456"),
    ],
)
def test_fhir_error_handler_resource_reference_formatting(
    resource_type, fhir_id, operation, expected_resource_ref
):
    """FHIRErrorHandler formats resource references correctly for different scenarios."""
    mock_exception = Mock()
    mock_exception.status_code = 404

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(
            mock_exception, resource_type, fhir_id, operation
        )

    error = exc_info.value
    assert f"{operation} {expected_resource_ref} failed" in error.message


def test_fhir_error_handler_fallback_and_unknown_error_handling():
    """FHIRErrorHandler handles message parsing fallback and unknown errors appropriately."""
    # Test message parsing fallback when status_code attribute missing
    mock_exception = Mock()
    mock_exception.status_code = None
    mock_exception.__str__ = Mock(return_value="HTTP 422: Validation failed")

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(mock_exception, "Patient", "123", "create")

    error = exc_info.value
    assert "Proposed resource violated applicable FHIR profiles" in error.message
    assert error.state == "422"

    # Test unknown error fallback
    mock_unknown = Mock()
    mock_unknown.status_code = 999  # Unknown status code
    mock_unknown.__str__ = Mock(return_value="Unknown server error")

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(mock_unknown, "Patient", "123", "delete")

    error = exc_info.value
    assert "delete Patient/123 failed: HTTP error" in error.message
    assert error.code == "Unknown server error"
    assert error.state == "999"


@pytest.mark.parametrize(
    "error_type,args,expected_content,expected_code,expected_state",
    [
        # Validation errors
        (
            "validation",
            {
                "message": "Missing required field",
                "resource_type": "Patient",
                "field_name": "name",
            },
            "Validation failed for Patient.name: Missing required field",
            "VALIDATION_ERROR",
            "422",
        ),
        # Connection errors
        (
            "connection",
            {"message": "Connection timeout", "source": "Epic FHIR Server"},
            "Connection to source 'Epic FHIR Server' failed: Connection timeout",
            "CONNECTION_ERROR",
            "503",
        ),
        # Authentication errors
        (
            "authentication",
            {"message": "Invalid credentials", "source": "Cerner FHIR"},
            "Authentication to source 'Cerner FHIR' failed: Invalid credentials",
            "AUTHENTICATION_ERROR",
            "401",
        ),
    ],
)
def test_fhir_error_handler_specialized_error_creation(
    error_type, args, expected_content, expected_code, expected_state
):
    """FHIRErrorHandler creates properly formatted specialized errors."""
    if error_type == "validation":
        error = FHIRErrorHandler.create_validation_error(**args)
    elif error_type == "connection":
        error = FHIRErrorHandler.create_connection_error(**args)
    elif error_type == "authentication":
        error = FHIRErrorHandler.create_authentication_error(**args)

    assert isinstance(error, FHIRConnectionError)
    assert error.message == expected_content
    assert error.code == expected_code
    assert error.state == expected_state
