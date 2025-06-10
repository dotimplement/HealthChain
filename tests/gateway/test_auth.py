"""
Tests for the OAuth2 authentication module in the HealthChain gateway system.

This module tests OAuth2 token management, configuration, and connection string parsing.
"""

import pytest
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
def fhir_auth_config():
    """Create a FHIR authentication configuration for testing."""
    return FHIRAuthConfig(
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://example.com/oauth/token",
        base_url="https://example.com/fhir/R4",
        scope="system/*.read system/*.write",
        audience="https://example.com/fhir",
    )


@pytest.fixture
def token_manager(oauth2_config):
    """Create an OAuth2TokenManager for testing."""
    return OAuth2TokenManager(oauth2_config)


@pytest.fixture
def mock_token_response():
    """Create a mock token response."""
    return {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "system/*.read",
    }


class TestOAuth2Config:
    """Test OAuth2Config model."""

    def test_oauth2_config_creation(self):
        """Test OAuth2Config can be created with required fields."""
        config = OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://example.com/token",
        )
        assert config.client_id == "test_client"
        assert config.client_secret == "test_secret"
        assert config.token_url == "https://example.com/token"
        assert config.scope is None
        assert config.audience is None

    def test_oauth2_config_with_optional_fields(self):
        """Test OAuth2Config with all optional fields."""
        config = OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://example.com/token",
            scope="system/*.read",
            audience="https://example.com/fhir",
            use_jwt_assertion=True,
        )
        assert config.scope == "system/*.read"
        assert config.audience == "https://example.com/fhir"
        assert config.use_jwt_assertion is True


class TestTokenInfo:
    """Test TokenInfo model."""

    def test_token_info_from_response(self, mock_token_response):
        """Test TokenInfo creation from OAuth2 response."""
        token_info = TokenInfo.from_response(mock_token_response)

        assert token_info.access_token == "test_access_token"
        assert token_info.token_type == "Bearer"
        assert token_info.expires_in == 3600
        assert token_info.scope == "system/*.read"
        assert isinstance(token_info.expires_at, datetime)

    def test_token_info_from_response_minimal(self):
        """Test TokenInfo creation with minimal response data."""
        minimal_response = {"access_token": "test_token"}
        token_info = TokenInfo.from_response(minimal_response)

        assert token_info.access_token == "test_token"
        assert token_info.token_type == "Bearer"  # Default value
        assert token_info.expires_in == 3600  # Default value
        assert token_info.scope is None

    def test_token_is_expired(self):
        """Test token expiration check."""
        # Create expired token
        expired_token = TokenInfo(
            access_token="test_token",
            expires_in=3600,
            expires_at=datetime.now() - timedelta(minutes=10),
        )
        assert expired_token.is_expired()

        # Create valid token
        valid_token = TokenInfo(
            access_token="test_token",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert not valid_token.is_expired()

    def test_token_expiry_buffer(self):
        """Test token expiration with buffer time."""
        # Token expires in 4 minutes, buffer is 5 minutes
        near_expiry_token = TokenInfo(
            access_token="test_token",
            expires_in=240,
            expires_at=datetime.now() + timedelta(minutes=4),
        )
        assert near_expiry_token.is_expired(buffer_seconds=300)  # 5 minutes buffer

        # Token expires in 6 minutes, buffer is 5 minutes
        safe_token = TokenInfo(
            access_token="test_token",
            expires_in=360,
            expires_at=datetime.now() + timedelta(minutes=6),
        )
        assert not safe_token.is_expired(buffer_seconds=300)  # 5 minutes buffer


class TestOAuth2TokenManager:
    """Test OAuth2TokenManager functionality."""

    def test_token_manager_initialization(self, token_manager, oauth2_config):
        """Test token manager initializes correctly."""
        assert token_manager.config == oauth2_config
        assert token_manager.refresh_buffer_seconds == 300
        assert token_manager._token is None

    @patch("httpx.AsyncClient.post")
    async def test_get_access_token_fresh(
        self, mock_post, token_manager, mock_token_response
    ):
        """Test getting access token when none exists."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        token = await token_manager.get_access_token()

        assert token == "test_access_token"
        assert token_manager._token is not None
        assert token_manager._token.access_token == "test_access_token"
        mock_post.assert_called_once()

    @patch("httpx.AsyncClient.post")
    async def test_get_access_token_cached(self, mock_post, token_manager):
        """Test getting access token when valid token exists."""
        # Set up existing valid token
        token_manager._token = TokenInfo(
            access_token="cached_token",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )

        token = await token_manager.get_access_token()

        assert token == "cached_token"
        mock_post.assert_not_called()

    @patch("httpx.AsyncClient.post")
    async def test_token_refresh_on_expiry(
        self, mock_post, token_manager, mock_token_response
    ):
        """Test token refresh when existing token is expired."""
        # Set up expired token
        token_manager._token = TokenInfo(
            access_token="expired_token",
            expires_in=3600,
            expires_at=datetime.now() - timedelta(minutes=10),
        )

        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        token = await token_manager.get_access_token()

        assert token == "test_access_token"
        mock_post.assert_called_once()

    @patch("httpx.AsyncClient.post")
    async def test_token_refresh_http_error(self, mock_post, token_manager):
        """Test token refresh failure handling."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        from httpx import HTTPStatusError, Request

        mock_post.side_effect = HTTPStatusError(
            "401 Unauthorized", request=Mock(spec=Request), response=mock_response
        )

        with pytest.raises(Exception, match="Failed to refresh token: 401"):
            await token_manager.get_access_token()

    def test_invalidate_token(self, token_manager):
        """Test token invalidation."""
        token_manager._token = TokenInfo(
            access_token="test_token",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )

        token_manager.invalidate_token()
        assert token_manager._token is None


class TestFHIRAuthConfig:
    """Test FHIRAuthConfig model."""

    def test_fhir_auth_config_creation(self):
        """Test FHIRAuthConfig creation with required fields."""
        config = FHIRAuthConfig(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://example.com/token",
            base_url="https://example.com/fhir/R4",
        )

        assert config.client_id == "test_client"
        assert config.base_url == "https://example.com/fhir/R4"
        assert config.scope == "system/*.read system/*.write"
        assert config.timeout == 30
        assert config.verify_ssl is True

    def test_fhir_auth_config_with_jwt_assertion(self):
        """Test FHIRAuthConfig with JWT assertion enabled."""
        config = FHIRAuthConfig(
            client_id="test_client",
            client_secret="/path/to/private_key.pem",  # Path for JWT assertion
            token_url="https://example.com/token",
            base_url="https://example.com/fhir/R4",
            use_jwt_assertion=True,
        )

        assert config.use_jwt_assertion is True
        assert config.client_secret == "/path/to/private_key.pem"

    def test_to_oauth2_config(self, fhir_auth_config):
        """Test conversion to OAuth2Config."""
        oauth2_config = fhir_auth_config.to_oauth2_config()

        assert oauth2_config.client_id == fhir_auth_config.client_id
        assert oauth2_config.client_secret == fhir_auth_config.client_secret
        assert oauth2_config.token_url == fhir_auth_config.token_url
        assert oauth2_config.scope == fhir_auth_config.scope
        assert oauth2_config.audience == fhir_auth_config.audience
        assert oauth2_config.use_jwt_assertion == fhir_auth_config.use_jwt_assertion


class TestConnectionStringParsing:
    """Test FHIR connection string parsing."""

    def test_parse_basic_connection_string(self):
        """Test parsing a basic FHIR connection string."""
        connection_string = (
            "fhir://example.com/fhir/R4?"
            "client_id=test_client&"
            "client_secret=test_secret&"
            "token_url=https://example.com/token"
        )

        config = parse_fhir_auth_connection_string(connection_string)

        assert config.client_id == "test_client"
        assert config.client_secret == "test_secret"
        assert config.token_url == "https://example.com/token"
        assert config.base_url == "https://example.com/fhir/R4"

    def test_parse_full_connection_string(self):
        """Test parsing connection string with all parameters."""
        connection_string = (
            "fhir://example.com:8080/fhir/R4?"
            "client_id=test_client&"
            "client_secret=test_secret&"
            "token_url=https://example.com/token&"
            "scope=system/*.read&"
            "audience=https://example.com/fhir&"
            "timeout=60&"
            "verify_ssl=false&"
            "use_jwt_assertion=true"
        )

        config = parse_fhir_auth_connection_string(connection_string)

        assert config.client_id == "test_client"
        assert config.base_url == "https://example.com:8080/fhir/R4"
        assert config.scope == "system/*.read"
        assert config.audience == "https://example.com/fhir"
        assert config.timeout == 60
        assert config.verify_ssl is False
        assert config.use_jwt_assertion is True

    def test_parse_with_port_number(self):
        """Test parsing connection string with port number."""
        connection_string = (
            "fhir://localhost:8080/fhir/R4?"
            "client_id=test_client&"
            "client_secret=test_secret&"
            "token_url=https://localhost:8080/oauth/token"
        )

        config = parse_fhir_auth_connection_string(connection_string)

        assert config.base_url == "https://localhost:8080/fhir/R4"
        assert config.token_url == "https://localhost:8080/oauth/token"

    def test_parse_invalid_connection_string(self):
        """Test parsing invalid connection string raises error."""
        with pytest.raises(
            ValueError, match="Connection string must start with fhir://"
        ):
            parse_fhir_auth_connection_string("invalid://not-fhir")

    def test_parse_missing_required_params(self):
        """Test parsing connection string with missing required parameters."""
        connection_string = "fhir://example.com/fhir/R4?client_id=test_client"

        with pytest.raises(ValueError, match="Missing required parameters"):
            parse_fhir_auth_connection_string(connection_string)

    def test_parse_missing_client_secret(self):
        """Test parsing connection string missing client_secret."""
        connection_string = (
            "fhir://example.com/fhir/R4?"
            "client_id=test_client&"
            "token_url=https://example.com/token"
        )

        with pytest.raises(ValueError, match="Missing required parameters"):
            parse_fhir_auth_connection_string(connection_string)

    def test_parse_missing_token_url(self):
        """Test parsing connection string missing token_url."""
        connection_string = (
            "fhir://example.com/fhir/R4?"
            "client_id=test_client&"
            "client_secret=test_secret"
        )

        with pytest.raises(ValueError, match="Missing required parameters"):
            parse_fhir_auth_connection_string(connection_string)

    def test_parse_url_encoded_parameters(self):
        """Test parsing connection string with URL-encoded parameters."""
        connection_string = (
            "fhir://example.com/fhir/R4?"
            "client_id=test%20client&"
            "client_secret=test%20secret&"
            "token_url=https%3A//example.com/token&"
            "scope=system%2F*.read"
        )

        config = parse_fhir_auth_connection_string(connection_string)

        assert config.client_id == "test client"
        assert config.client_secret == "test secret"
        assert config.token_url == "https://example.com/token"
        assert config.scope == "system/*.read"
