"""
Tests for the OAuth2 authentication module in the HealthChain gateway system.

This module tests OAuth2 token management, configuration, and connection string parsing.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from healthchain.gateway.clients.auth import (
    OAuth2Config,
    TokenInfo,
    OAuth2TokenManager,
    FHIRAuthConfig,
    parse_fhir_auth_connection_string,
)

# Configure pytest-anyio for async tests
pytestmark = pytest.mark.anyio


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
def token_manager(oauth2_config):
    """Create an OAuth2TokenManager for testing."""
    return OAuth2TokenManager(oauth2_config)


@pytest.fixture
def token_manager_jwt(oauth2_config_jwt):
    """Create an OAuth2TokenManager for JWT testing."""
    return OAuth2TokenManager(oauth2_config_jwt)


@pytest.fixture
def mock_token_response():
    """Create a mock token response."""
    return {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "system/*.read",
    }


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


# Core Validation Tests
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
        # JWT without path
        (
            {
                "client_id": "test",
                "client_secret": "secret",
                "token_url": "https://example.com/token",
                "use_jwt_assertion": True,
            },
            "use_jwt_assertion=True requires client_secret_path to be set",
        ),
        # Path without JWT
        (
            {
                "client_id": "test",
                "client_secret_path": "/path",
                "token_url": "https://example.com/token",
                "use_jwt_assertion": False,
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


# Token Management Core Tests
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


@patch("httpx.AsyncClient.post")
async def test_oauth2_token_manager_standard_flow(
    mock_post, token_manager, mock_token_response
):
    """OAuth2TokenManager performs standard client credentials flow correctly."""
    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = mock_token_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    token = await token_manager.get_access_token()

    # Verify token returned
    assert token == "test_access_token"

    # Verify correct request data for standard flow
    call_args = mock_post.call_args
    request_data = call_args[1]["data"]
    assert request_data["grant_type"] == "client_credentials"
    assert request_data["client_id"] == "test_client"
    assert request_data["client_secret"] == "test_secret"
    assert "client_assertion" not in request_data


@patch("healthchain.gateway.clients.auth.OAuth2TokenManager._create_jwt_assertion")
@patch("httpx.AsyncClient.post")
async def test_oauth2_token_manager_jwt_flow(
    mock_post, mock_create_jwt, token_manager_jwt, mock_token_response
):
    """OAuth2TokenManager performs JWT assertion flow correctly."""
    mock_create_jwt.return_value = "mock_jwt_assertion"

    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = mock_token_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    token = await token_manager_jwt.get_access_token()
    assert token == "test_access_token"

    # Verify JWT-specific request data
    call_args = mock_post.call_args
    request_data = call_args[1]["data"]
    assert request_data["grant_type"] == "client_credentials"
    assert (
        request_data["client_assertion_type"]
        == "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
    )
    assert request_data["client_assertion"] == "mock_jwt_assertion"
    assert "client_secret" not in request_data


@patch("httpx.AsyncClient.post")
async def test_oauth2_token_manager_caching_and_refresh(
    mock_post, token_manager, mock_token_response
):
    """OAuth2TokenManager caches valid tokens and refreshes expired ones."""
    # Set up valid cached token
    token_manager._token = TokenInfo(
        access_token="cached_token",
        expires_in=3600,
        expires_at=datetime.now() + timedelta(hours=1),
    )

    # Should use cached token
    token = await token_manager.get_access_token()
    assert token == "cached_token"
    mock_post.assert_not_called()

    # Set expired token
    token_manager._token = TokenInfo(
        access_token="expired_token",
        expires_in=3600,
        expires_at=datetime.now() - timedelta(minutes=10),
    )

    # Mock refresh response
    mock_response = Mock()
    mock_response.json.return_value = mock_token_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Should refresh token
    token = await token_manager.get_access_token()
    assert token == "test_access_token"
    mock_post.assert_called_once()


@patch("httpx.AsyncClient.post")
async def test_oauth2_token_manager_error_handling(mock_post, token_manager):
    """OAuth2TokenManager handles HTTP errors gracefully."""
    from httpx import HTTPStatusError, Request

    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_post.side_effect = HTTPStatusError(
        "401 Unauthorized", request=Mock(spec=Request), response=mock_response
    )

    with pytest.raises(Exception, match="Failed to refresh token: 401"):
        await token_manager.get_access_token()


@patch("jwt.JWT.encode")
@patch("jwt.jwk_from_pem")
def test_oauth2_token_manager_jwt_assertion_creation(
    mock_jwk_from_pem, mock_jwt_encode, token_manager_jwt, temp_key_file
):
    """OAuth2TokenManager creates valid JWT assertions with correct claims."""
    token_manager_jwt.config.client_secret_path = temp_key_file

    mock_key = Mock()
    mock_jwk_from_pem.return_value = mock_key
    mock_jwt_encode.return_value = "signed_jwt_token"

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


# FHIR Config Tests (Core Validation Only)
def test_fhir_auth_config_validation_mirrors_oauth2_config():
    """FHIRAuthConfig enforces same validation rules as OAuth2Config."""
    # Should fail with same validation error
    with pytest.raises(
        ValueError, match="Either client_secret or client_secret_path must be provided"
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


# Connection String Parsing Tests (Core Functionality)
@pytest.mark.parametrize(
    "connection_string,expected_error",
    [
        # Invalid scheme
        ("invalid://not-fhir", "Connection string must start with fhir://"),
        # Missing required params
        (
            "fhir://example.com/fhir/R4?client_id=test_client",
            "Missing required parameters",
        ),
        # Missing secrets
        (
            "fhir://example.com/fhir/R4?client_id=test&token_url=https://example.com/token",
            "Either 'client_secret' or 'client_secret_path' parameter must be provided",
        ),
        # Both secrets
        (
            "fhir://example.com/fhir/R4?client_id=test&client_secret=secret&client_secret_path=/path&token_url=https://example.com/token",
            "Cannot provide both 'client_secret' and 'client_secret_path' parameters",
        ),
    ],
)
def test_connection_string_parsing_validation(connection_string, expected_error):
    """Connection string parsing enforces validation rules."""
    with pytest.raises(ValueError, match=expected_error):
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
