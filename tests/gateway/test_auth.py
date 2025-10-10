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
)
from healthchain.gateway.clients.fhir.base import (
    FHIRAuthConfig,
    parse_fhir_auth_connection_string,
)
from healthchain.gateway.clients.fhir.sync.client import FHIRClient


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


@patch("httpx.Client.post")
def test_oauth2_token_manager_standard_flow(
    mock_post, token_manager, mock_token_response
):
    """OAuth2TokenManager performs standard client credentials flow correctly."""
    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = mock_token_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    token = token_manager.get_access_token()

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
@patch("httpx.Client.post")
def test_oauth2_token_manager_jwt_flow(
    mock_post, mock_create_jwt, token_manager_jwt, mock_token_response
):
    """OAuth2TokenManager performs JWT assertion flow correctly."""
    mock_create_jwt.return_value = "mock_jwt_assertion"

    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = mock_token_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    token = token_manager_jwt.get_access_token()
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


@patch("httpx.Client.post")
def test_oauth2_token_manager_caching_and_refresh(
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
    token = token_manager.get_access_token()
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
    token = token_manager.get_access_token()
    assert token == "test_access_token"
    mock_post.assert_called_once()


@patch("httpx.Client.post")
def test_oauth2_token_manager_error_handling(mock_post, token_manager):
    """OAuth2TokenManager handles HTTP errors gracefully."""
    from httpx import HTTPStatusError, Request

    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_post.side_effect = HTTPStatusError(
        "401 Unauthorized", request=Mock(spec=Request), response=mock_response
    )

    with pytest.raises(Exception, match="Failed to refresh token: 401"):
        token_manager.get_access_token()


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


def test_oauth2_token_manager_thread_safety():
    """OAuth2TokenManager handles concurrent token requests safely using threading.Lock."""
    import time
    from concurrent.futures import ThreadPoolExecutor

    config = OAuth2Config(
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://test.fhir.org/oauth/token",
    )

    token_manager = OAuth2TokenManager(config)

    # Mock the token refresh to track calls
    refresh_calls = []

    def tracked_refresh():
        refresh_calls.append(time.time())
        # Simulate network delay
        time.sleep(0.1)
        # Create a mock token that won't expire during test
        from datetime import datetime, timedelta

        token_manager._token = TokenInfo(
            access_token="test_token",
            expires_in=3600,  # Long expiry to avoid expiration during test
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(seconds=3600),
        )

    token_manager._refresh_token = tracked_refresh

    # Test concurrent access with multiple threads
    def get_token():
        return token_manager.get_access_token()

    # Run multiple threads concurrently trying to get token
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_token) for _ in range(5)]
        tokens = [future.result() for future in futures]

    # All threads should get the same token
    assert all(token == "test_token" for token in tokens)

    # Only one refresh should have occurred due to thread safety
    assert len(refresh_calls) == 1, f"Expected 1 refresh call, got {len(refresh_calls)}"


def test_oauth2_token_manager_uses_threading_lock():
    """OAuth2TokenManager uses threading.Lock for synchronization."""
    import threading

    config = OAuth2Config(
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://test.fhir.org/oauth/token",
    )

    token_manager = OAuth2TokenManager(config)

    # Verify that the token manager has a threading lock
    assert hasattr(token_manager, "_refresh_lock")
    assert isinstance(token_manager._refresh_lock, type(threading.Lock()))


def test_sync_token_manager_methods_are_not_async():
    """Sync OAuth2TokenManager methods are synchronous, not async."""
    import inspect

    config = OAuth2Config(
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://test.fhir.org/oauth/token",
    )

    token_manager = OAuth2TokenManager(config)

    # Verify get_access_token is not a coroutine function
    assert not inspect.iscoroutinefunction(token_manager.get_access_token)
    assert not inspect.iscoroutinefunction(token_manager._refresh_token)

    # Test that calling the method doesn't return a coroutine
    # Mock the token refresh method directly to avoid HTTP calls
    from datetime import datetime, timedelta

    with patch.object(token_manager, "_refresh_token") as mock_refresh:

        def mock_refresh_side_effect():
            token_manager._token = TokenInfo(
                access_token="test_token",
                expires_in=3600,
                token_type="Bearer",
                expires_at=datetime.now() + timedelta(seconds=3600),
            )

        mock_refresh.side_effect = mock_refresh_side_effect

        result = token_manager.get_access_token()

        # Result should be a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)
        assert result == "test_token"


def test_sync_vs_async_token_manager_distinction():
    """OAuth2TokenManager (sync) and AsyncOAuth2TokenManager (async) have distinct behaviors."""
    from healthchain.gateway.clients.auth import AsyncOAuth2TokenManager
    import inspect

    config = OAuth2Config(
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://test.fhir.org/oauth/token",
    )

    sync_manager = OAuth2TokenManager(config)
    async_manager = AsyncOAuth2TokenManager(config)

    # Sync manager should have threading.Lock
    assert hasattr(sync_manager, "_refresh_lock")
    assert isinstance(sync_manager._refresh_lock, type(__import__("threading").Lock()))

    # Async manager should have asyncio.Lock (or None initially)
    assert hasattr(async_manager, "_refresh_lock")
    assert async_manager._refresh_lock is None  # Created lazily

    # Method signatures should be different
    assert not inspect.iscoroutinefunction(sync_manager.get_access_token)
    assert inspect.iscoroutinefunction(async_manager.get_access_token)


def test_public_endpoint_mode_behaviors():
    """Public endpoint: parse config, no auth required, no token, no Authorization header."""
    connection_string = (
        "fhir://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    )

    config = parse_fhir_auth_connection_string(connection_string)

    assert (
        config.base_url
        == "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    )
    assert config.requires_auth is False

    client = FHIRClient(auth_config=config)
    assert client.token_manager is None

    headers = client._get_headers()
    assert "Authorization" not in headers
    assert headers["Accept"] == "application/fhir+json"
    assert headers["Content-Type"] == "application/fhir+json"


def test_parse_connection_string_with_auth():
    """Connection string with auth params creates authenticated config."""
    connection_string = (
        "fhir://epic.com/api/FHIR/R4"
        "?client_id=test_app"
        "&client_secret=test_secret"
        "&token_url=https://epic.com/oauth2/token"
    )

    config = parse_fhir_auth_connection_string(connection_string)

    assert config.base_url == "https://epic.com/api/FHIR/R4"
    assert config.requires_auth is True
    assert config.client_id == "test_app"
    assert config.client_secret == "test_secret"
    assert config.token_url == "https://epic.com/oauth2/token"


@pytest.mark.parametrize(
    "config_kwargs,error",
    [
        (
            {"base_url": "https://epic.com/api/FHIR/R4", "client_id": "test_app"},
            "token_url is required",
        ),
        (
            {
                "base_url": "https://epic.com/api/FHIR/R4",
                "client_id": "test_app",
                "token_url": "https://epic.com/token",
            },
            "Either client_secret or client_secret_path",
        ),
        (
            {
                "base_url": "https://epic.com/api/FHIR/R4",
                "client_id": "test_app",
                "client_secret": "secret",
                "token_url": "https://epic.com/token",
                "use_jwt_assertion": True,
            },
            "requires client_secret_path",
        ),
    ],
)
def test_fhir_auth_config_validation_rules(config_kwargs, error):
    """FHIRAuthConfig enforces validation rules for authenticated configs."""
    with pytest.raises(ValueError, match=error):
        FHIRAuthConfig(**config_kwargs)


def test_to_connection_string_roundtrip():
    """FHIRAuthConfig serializes to and parses from connection string consistently."""
    cfg = FHIRAuthConfig(
        base_url="https://epic.com/api/FHIR/R4",
        client_id="app",
        client_secret="secret",
        token_url="https://epic.com/token",
        scope="system/*.read",
        timeout=45,
        verify_ssl=False,
    )
    conn = cfg.to_connection_string()
    parsed = parse_fhir_auth_connection_string(conn)
    assert parsed.base_url == cfg.base_url
    assert parsed.client_id == cfg.client_id
    assert parsed.token_url == cfg.token_url
    assert parsed.timeout == 45
    assert parsed.verify_ssl is False


def test_from_env_missing_vars_raises(monkeypatch):
    """from_env raises when required env vars are missing."""
    for key in ["EPIC_CLIENT_ID", "EPIC_TOKEN_URL", "EPIC_BASE_URL"]:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="Missing required environment variables"):
        FHIRAuthConfig.from_env("EPIC")
