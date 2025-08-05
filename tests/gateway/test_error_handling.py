"""Tests for FHIR error handling functionality."""

import pytest

from healthchain.gateway.fhir.errors import (
    FHIRConnectionError,
    FHIRErrorHandler,
)


@pytest.mark.parametrize(
    "show_state,expected",
    [
        (True, "[404 NOT_FOUND] Resource not found"),
        (False, "[VALIDATION_ERROR] Validation failed"),
        (None, "[None GENERIC_ERROR] Generic error"),  # no state provided
    ],
)
def test_fhir_connection_error_formatting(show_state, expected):
    """FHIRConnectionError formats messages correctly based on show_state."""
    if show_state is None:
        error = FHIRConnectionError(message="Generic error", code="GENERIC_ERROR")
    elif show_state:
        error = FHIRConnectionError(
            message="Resource not found", code="NOT_FOUND", state="404", show_state=True
        )
    else:
        error = FHIRConnectionError(
            message="Validation failed",
            code="VALIDATION_ERROR",
            state="422",
            show_state=False,
        )

    assert str(error) == expected


@pytest.mark.parametrize(
    "status_code,expected_fragment",
    [
        (400, "Resource could not be parsed"),
        (401, "Authorization is required"),
        (403, "You may not have permission"),
        (404, "resource you are looking for does not exist"),
        (405, "server does not allow client defined ids"),
        (409, "Version conflict - update cannot be done"),
        (410, "resource you are looking for is no longer available"),
        (412, "Version conflict - version id does not match"),
        (422, "Proposed resource violated applicable FHIR profiles"),
    ],
)
def test_error_mapping_by_status_code(status_code, expected_fragment):
    """FHIRErrorHandler maps HTTP status codes to appropriate FHIR error messages."""
    mock_exception = Exception("HTTP error")
    mock_exception.status_code = status_code

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(
            mock_exception, resource_type="Patient", fhir_id="123", operation="read"
        )

    error = exc_info.value
    assert expected_fragment.lower() in error.message.lower()
    assert error.state == str(status_code)
    assert "read Patient/123 failed" in error.message


def test_error_mapping_by_message_content():
    """FHIRErrorHandler maps errors by parsing status code from error message."""
    mock_exception = Exception("Request failed with status 404 - not found")

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(
            mock_exception, resource_type="Observation", operation="search"
        )

    error = exc_info.value
    assert "resource you are looking for does not exist" in error.message
    assert error.state == "404"
    assert "search Observation failed" in error.message


@pytest.mark.parametrize(
    "has_status_code,expected_state",
    [
        (True, "599"),
        (False, "UNKNOWN"),
    ],
)
def test_error_handling_edge_cases(has_status_code, expected_state):
    """FHIRErrorHandler handles unknown status codes and missing attributes."""
    mock_exception = Exception("Server error")
    if has_status_code:
        mock_exception.status_code = 599  # Unknown status code

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(
            mock_exception, resource_type="Patient", fhir_id="123", operation="update"
        )

    error = exc_info.value
    assert error.state == expected_state
    assert "update Patient/123 failed: HTTP error" in error.message


@pytest.mark.parametrize(
    "fhir_id,expected_format",
    [
        ("patient-123", "read Patient/patient-123 failed"),
        (None, "create Patient failed"),
    ],
)
def test_resource_reference_formatting(fhir_id, expected_format):
    """FHIRErrorHandler formats resource references correctly with or without ID."""
    mock_exception = Exception("Error")
    mock_exception.status_code = 404 if fhir_id else 400

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(
            mock_exception,
            resource_type="Patient",
            fhir_id=fhir_id,
            operation="read" if fhir_id else "create",
        )

    assert expected_format in str(exc_info.value)


@pytest.mark.parametrize(
    "resource_type,field_name,expected_format",
    [
        (
            "Patient",
            "identifier",
            "Validation failed for Patient.identifier: Invalid format",
        ),
        (
            "Observation",
            None,
            "Validation failed for Observation: Missing required field",
        ),
        (None, None, "Validation failed: General validation error"),
    ],
)
def test_validation_error_creation(resource_type, field_name, expected_format):
    """FHIRErrorHandler creates validation errors with appropriate formatting."""
    message = (
        "Invalid format"
        if field_name
        else "Missing required field"
        if resource_type
        else "General validation error"
    )

    error = FHIRErrorHandler.create_validation_error(
        message=message, resource_type=resource_type, field_name=field_name
    )

    assert error.message == expected_format
    assert error.code == "VALIDATION_ERROR"
    assert error.state == "422"


@pytest.mark.parametrize(
    "source,error_type,expected_code,expected_state",
    [
        ("epic_prod", "connection", "CONNECTION_ERROR", "503"),
        ("cerner_dev", "authentication", "AUTHENTICATION_ERROR", "401"),
        (None, "connection", "CONNECTION_ERROR", "503"),
        (None, "authentication", "AUTHENTICATION_ERROR", "401"),
    ],
)
def test_specialized_error_creation(source, error_type, expected_code, expected_state):
    """FHIRErrorHandler creates connection and authentication errors correctly."""
    message = "Network timeout" if error_type == "connection" else "Invalid token"

    if error_type == "connection":
        error = FHIRErrorHandler.create_connection_error(message=message, source=source)
        expected_prefix = f"Connection to source '{source}'" if source else "Connection"
    else:
        error = FHIRErrorHandler.create_authentication_error(
            message=message, source=source
        )
        expected_prefix = (
            f"Authentication to source '{source}'" if source else "Authentication"
        )

    expected_message = (
        f"{expected_prefix} failed: {message}"
        if source
        else f"{expected_prefix} failed: {message}"
    )

    assert error.message == expected_message
    assert error.code == expected_code
    assert error.state == expected_state


def test_error_chaining_preserves_original_message():
    """FHIRErrorHandler preserves original exception message in error code."""
    original_message = "Detailed server error: Resource validation failed on field X"
    mock_exception = Exception(original_message)
    mock_exception.status_code = 422

    with pytest.raises(FHIRConnectionError) as exc_info:
        FHIRErrorHandler.handle_fhir_error(
            mock_exception, resource_type="Patient", operation="create"
        )

    assert exc_info.value.code == original_message
