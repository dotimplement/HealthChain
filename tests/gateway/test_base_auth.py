"""
Tests for shared OAuth2 authentication functionality in the HealthChain gateway system.

This module tests shared validation logic, configuration, and connection string parsing
that should work identically across sync and async implementations.
"""

import pytest
import tempfile
import os
from unittest.mock import patch
from datetime import datetime, timedelta

from healthchain.gateway.clients.auth import (
    OAuth2Config,
    TokenInfo,
    OAuth2TokenManager,
)
from healthchain.gateway.clients.fhir.base import (
    FHIRAuthConfig,
    parse_fhir_auth_connection_string,
)


@pytest.fixture
def oauth2_config():
    """Create a basic OAuth2 configuration for testing."""
    return OAuth2Config(
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://example.com/oauth/token",
        scope="system/*.read",
        audience="https://example.com/fhir",
    )


@pytest.fixture
def oauth2_config_jwt():
    """Create an OAuth2 configuration for JWT assertion testing."""
    return OAuth2Config(
        client_id="test_client",
        client_secret_path="/path/to/private.pem",
        token_url="https://example.com/oauth/token",
        scope="system/*.read",
        audience="https://example.com/fhir",
        use_jwt_assertion=True,
    )


@pytest.fixture
def temp_key_file():
    """Create a temporary private key file for testing."""
    key_content = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC4f6a8v...
-----END PRIVATE KEY-----"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
        f.write(key_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.mark.parametrize(
    "config_args,expected_error",
    [
        # Missing both secrets
        (
            {"client_id": "test", "token_url": "https://example.com/token"},
            "Either client_secret or client_secret_path must be provided",
        ),
        # Both secrets provided
        (
            {
                "client_id": "test",
                "client_secret": "secret",
                "client_secret_path": "/path",
                "token_url": "https://example.com/token",
            },
            "Cannot provide both client_secret and client_secret_path",
        ),
        # client_secret_path without JWT assertion
        (
            {
                "client_id": "test",
                "client_secret_path": "/path",
                "token_url": "https://example.com/token",
            },
            "client_secret_path can only be used with use_jwt_assertion=True",
        ),
    ],
)
def test_oauth2_config_validation_rules(config_args, expected_error):
    """OAuth2Config enforces validation rules for secret configuration."""
    with pytest.raises(ValueError, match=expected_error):
        OAuth2Config(**config_args)


def test_oauth2_config_secret_value_reads_from_file(temp_key_file):
    """OAuth2Config reads secret from file when client_secret_path is provided."""
    config = OAuth2Config(
        client_id="test_client",
        client_secret_path=temp_key_file,
        token_url="https://example.com/token",
        use_jwt_assertion=True,
    )
    secret_value = config.secret_value
    assert "BEGIN PRIVATE KEY" in secret_value
    assert "END PRIVATE KEY" in secret_value


def test_oauth2_config_secret_value_handles_file_errors():
    """OAuth2Config raises clear error when file cannot be read."""
    config = OAuth2Config(
        client_id="test_client",
        client_secret_path="/nonexistent/file.pem",
        token_url="https://example.com/token",
        use_jwt_assertion=True,
    )
    with pytest.raises(ValueError, match="Failed to read secret from"):
        _ = config.secret_value


def test_token_info_expiration_logic():
    """TokenInfo correctly calculates expiration with buffer."""
    # Test near-expiry with buffer
    near_expiry_token = TokenInfo(
        access_token="test_token",
        expires_in=240,
        expires_at=datetime.now() + timedelta(minutes=4),
    )
    assert near_expiry_token.is_expired(
        buffer_seconds=300
    )  # 5 min buffer, expires in 4
    assert not near_expiry_token.is_expired(
        buffer_seconds=120
    )  # 2 min buffer, expires in 4


@pytest.fixture
def token_manager_jwt(temp_key_file):
    """Create an OAuth2TokenManager for JWT testing - uses sync manager for shared logic testing."""
    oauth2_config_jwt = OAuth2Config(
        client_id="test_client",
        client_secret_path=temp_key_file,
        token_url="https://example.com/oauth/token",
        scope="system/*.read",
        audience="https://example.com/fhir",
        use_jwt_assertion=True,
    )
    return OAuth2TokenManager(oauth2_config_jwt)


@patch("jwt.JWT.encode")
@patch("jwt.jwk_from_pem")
def test_oauth2_token_manager_jwt_assertion_creation(
    mock_jwk_from_pem, mock_jwt_encode, token_manager_jwt
):
    """OAuth2TokenManager creates valid JWT assertions for authentication."""
    mock_jwt_encode.return_value = "signed_jwt_token"
    mock_jwk_from_pem.return_value = "mock_key"

    jwt_assertion = token_manager_jwt._create_jwt_assertion()

    assert jwt_assertion == "signed_jwt_token"

    # Verify JWT claims structure
    call_args = mock_jwt_encode.call_args[0]
    claims = call_args[0]
    assert claims["iss"] == "test_client"
    assert claims["sub"] == "test_client"
    assert claims["aud"] == "https://example.com/oauth/token"
    assert "jti" in claims
    assert "iat" in claims
    assert "exp" in claims


def test_fhir_auth_config_validation_mirrors_oauth2_config():
    """FHIRAuthConfig enforces same validation rules as OAuth2Config."""
    # Should fail with same validation error
    with pytest.raises(
        ValueError,
        match="Either client_secret or client_secret_path must be provided",
    ):
        FHIRAuthConfig(
            client_id="test_client",
            token_url="https://example.com/token",
            base_url="https://example.com/fhir/R4",
        )


def test_fhir_auth_config_to_oauth2_config_conversion():
    """FHIRAuthConfig correctly converts to OAuth2Config preserving all auth settings."""
    fhir_config = FHIRAuthConfig(
        client_id="test_client",
        client_secret_path="/path/to/private.pem",
        token_url="https://example.com/token",
        base_url="https://example.com/fhir/R4",
        use_jwt_assertion=True,
        scope="custom_scope",
        audience="custom_audience",
    )

    oauth2_config = fhir_config.to_oauth2_config()

    # Verify auth-related fields are preserved
    assert oauth2_config.client_id == fhir_config.client_id
    assert oauth2_config.client_secret_path == fhir_config.client_secret_path
    assert oauth2_config.token_url == fhir_config.token_url
    assert oauth2_config.use_jwt_assertion == fhir_config.use_jwt_assertion
    assert oauth2_config.scope == fhir_config.scope
    assert oauth2_config.audience == fhir_config.audience


@pytest.mark.parametrize(
    "connection_string,expected_error",
    [
        # Invalid scheme
        ("invalid://not-fhir", "Connection string must start with fhir://"),
        # Missing required params
        (
            "fhir://example.com/fhir/R4?client_id=test_client",
            "token_url is required",
        ),
        # Missing secrets
        (
            "fhir://example.com/fhir/R4?client_id=test&token_url=https://example.com/token",
            "Either client_secret or client_secret_path must be provided",
        ),
        # Both secrets
        (
            "fhir://example.com/fhir/R4?client_id=test&client_secret=secret&client_secret_path=/path&token_url=https://example.com/token",
            "Cannot provide both client_secret and client_secret_path",
        ),
    ],
)
def test_connection_string_parsing_validation(connection_string, expected_error):
    """Connection string parsing enforces validation rules."""
    with pytest.raises(Exception, match=expected_error):
        parse_fhir_auth_connection_string(connection_string)


def test_connection_string_parsing_handles_both_auth_types():
    """Connection string parsing correctly handles both standard and JWT authentication."""
    # Standard auth
    standard_string = "fhir://example.com/fhir/R4?client_id=test&client_secret=secret&token_url=https://example.com/token"
    standard_config = parse_fhir_auth_connection_string(standard_string)
    assert standard_config.client_secret == "secret"
    assert standard_config.client_secret_path is None
    assert not standard_config.use_jwt_assertion

    # JWT auth
    jwt_string = (
        "fhir://example.com/fhir/R4?client_id=test&client_secret_path=/path/key.pem&"
        "token_url=https://example.com/token&use_jwt_assertion=true"
    )
    jwt_config = parse_fhir_auth_connection_string(jwt_string)
    assert jwt_config.client_secret is None
    assert jwt_config.client_secret_path == "/path/key.pem"
    assert jwt_config.use_jwt_assertion


def test_connection_string_parsing_handles_complex_parameters():
    """Connection string parsing correctly handles all parameters and URL encoding."""
    connection_string = (
        "fhir://example.com:8080/fhir/R4?"
        "client_id=test%20client&"
        "client_secret=test%20secret&"
        "token_url=https%3A//example.com/token&"
        "scope=system%2F*.read&"
        "audience=https://example.com/fhir&"
        "timeout=60&"
        "verify_ssl=false"
    )

    config = parse_fhir_auth_connection_string(connection_string)

    assert config.client_id == "test client"  # URL decoded
    assert config.client_secret == "test secret"  # URL decoded
    assert config.token_url == "https://example.com/token"  # URL decoded
    assert config.scope == "system/*.read"  # URL decoded
    assert config.base_url == "https://example.com:8080/fhir/R4"
    assert config.audience == "https://example.com/fhir"
    assert config.timeout == 60
    assert not config.verify_ssl
