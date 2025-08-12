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
    AsyncOAuth2TokenManager,
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
def token_manager(oauth2_config):
    """Create an OAuth2TokenManager for testing."""
    return AsyncOAuth2TokenManager(oauth2_config)


@pytest.fixture
def token_manager_jwt(oauth2_config_jwt):
    """Create an OAuth2TokenManager for JWT testing."""
    return AsyncOAuth2TokenManager(oauth2_config_jwt)


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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
@patch("healthchain.gateway.clients.auth.AsyncOAuth2TokenManager._create_jwt_assertion")
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
