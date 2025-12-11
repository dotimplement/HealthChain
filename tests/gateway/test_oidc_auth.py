"""
Tests for OAuth2/OIDC authentication middleware and RBAC.

These tests verify JWT validation, OIDC integration, and role-based access control.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from healthchain.gateway.api.auth import (
    OIDCConfig,
    OIDCProvider,
    JWTAuthMiddleware,
    get_current_user,
    require_role,
)


# Test fixtures
@pytest.fixture
def oidc_config():
    """Create test OIDC configuration."""
    return OIDCConfig(
        issuer="https://test.example.com/realms/test",
        client_id="test-client",
        client_secret="test-secret",
        audience="test-api",
    )


@pytest.fixture
def mock_jwks():
    """Mock JWKS response."""
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-1",
                "use": "sig",
                "alg": "RS256",
                "n": "test-modulus",
                "e": "AQAB",
            }
        ]
    }


@pytest.fixture
def mock_well_known():
    """Mock OIDC discovery response."""
    return {
        "issuer": "https://test.example.com/realms/test",
        "jwks_uri": "https://test.example.com/realms/test/protocol/openid-connect/certs",
        "introspection_endpoint": "https://test.example.com/realms/test/protocol/openid-connect/token/introspect",
    }


class TestOIDCConfig:
    """Test OIDC configuration."""

    def test_oidc_config_creation(self):
        """Test creating OIDC config."""
        config = OIDCConfig(
            issuer="https://keycloak.example.com/realms/test",
            client_id="test-client",
            audience="test-api",
        )
        assert config.issuer == "https://keycloak.example.com/realms/test"
        assert config.client_id == "test-client"
        assert config.algorithms == ["RS256"]

    def test_issuer_trailing_slash_removed(self):
        """Test that trailing slash is removed from issuer."""
        config = OIDCConfig(
            issuer="https://keycloak.example.com/realms/test/",
            client_id="test-client",
        )
        assert config.issuer == "https://keycloak.example.com/realms/test"


class TestOIDCProvider:
    """Test OIDC provider functionality."""

    @pytest.mark.asyncio
    async def test_provider_initialization(self, oidc_config, mock_well_known):
        """Test OIDC provider initialization."""
        provider = OIDCProvider(oidc_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            # Mock well-known endpoint
            well_known_response = Mock()
            well_known_response.json.return_value = mock_well_known
            well_known_response.raise_for_status = Mock()
            mock_instance.get.return_value = well_known_response

            await provider.initialize()

            assert provider.config.jwks_uri == mock_well_known["jwks_uri"]
            assert (
                provider.config.token_introspection_uri
                == mock_well_known["introspection_endpoint"]
            )


class TestJWTAuthMiddleware:
    """Test JWT authentication middleware."""

    def test_excluded_path(self):
        """Test path exclusion logic."""
        app = FastAPI()
        middleware = JWTAuthMiddleware(
            app=app,
            oidc_provider=None,
            exclude_paths=["/docs", "/health", "/api/public/*"],
        )

        assert middleware._is_excluded_path("/docs")
        assert middleware._is_excluded_path("/health")
        assert middleware._is_excluded_path("/api/public/test")
        assert not middleware._is_excluded_path("/api/private")

    def test_extract_token(self):
        """Test token extraction from Authorization header."""
        app = FastAPI()
        middleware = JWTAuthMiddleware(app=app, oidc_provider=None)

        request = Mock()
        request.headers.get.return_value = "Bearer test-token"

        token = middleware._extract_token(request)
        assert token == "test-token"


class TestRoleDependencies:
    """Test role-based access control dependencies."""

    def test_extract_roles_keycloak(self):
        """Test extracting roles from Keycloak format."""
        from healthchain.gateway.api.auth.dependencies import _extract_roles

        user = {
            "realm_access": {"roles": ["doctor", "admin"]},
            "resource_access": {
                "healthchain-api": {"roles": ["api-user"]},
            },
        }
        roles = _extract_roles(user)
        assert "doctor" in roles
        assert "admin" in roles
        assert "api-user" in roles


class TestIntegration:
    """Integration tests for authentication flow."""

    def test_protected_endpoint_with_role(self):
        """Test accessing protected endpoint with correct role."""
        app = FastAPI()

        @app.get("/api/test")
        async def test_endpoint(user: dict = Depends(require_role("doctor"))):
            return {"message": "success"}

        def override_get_user():
            return {
                "sub": "user123",
                "realm_access": {"roles": ["doctor"]},
            }

        app.dependency_overrides[get_current_user] = override_get_user

        client = TestClient(app)
        response = client.get("/api/test")
        assert response.status_code == 200

    def test_protected_endpoint_without_role(self):
        """Test accessing protected endpoint without correct role."""
        app = FastAPI()

        @app.get("/api/test")
        async def test_endpoint(user: dict = Depends(require_role("admin"))):
            return {"message": "success"}

        def override_get_user():
            return {
                "sub": "user123",
                "realm_access": {"roles": ["doctor"]},
            }

        app.dependency_overrides[get_current_user] = override_get_user

        client = TestClient(app)
        response = client.get("/api/test")
        assert response.status_code == 403
