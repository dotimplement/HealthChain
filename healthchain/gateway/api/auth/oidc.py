"""
OIDC (OpenID Connect) provider configuration and integration.

Supports OIDC-compliant providers like Keycloak, Auth0, Okta, etc.
"""

import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class OIDCConfig(BaseModel):
    """
    Configuration for OIDC provider.

    This configuration supports standard OIDC-compliant identity providers
    including Keycloak, Auth0, Okta, Azure AD, and others.

    Example:
        ```python
        config = OIDCConfig(
            issuer="https://keycloak.example.com/realms/healthchain",
            client_id="healthchain-api",
            client_secret="your-secret",
            audience="healthchain-api"
        )
        ```
    """

    issuer: str = Field(
        ...,
        description="OIDC issuer URL (e.g., https://keycloak.example.com/realms/myrealm)",
    )
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: Optional[str] = Field(
        None, description="OAuth2 client secret (for token introspection)"
    )
    audience: Optional[str] = Field(
        None, description="Expected audience claim in JWT tokens"
    )
    jwks_uri: Optional[str] = Field(
        None, description="JWKS endpoint URL (auto-discovered if not provided)"
    )
    token_introspection_uri: Optional[str] = Field(
        None,
        description="Token introspection endpoint (auto-discovered if not provided)",
    )
    algorithms: List[str] = Field(
        default=["RS256"], description="Allowed JWT signing algorithms"
    )
    verify_exp: bool = Field(default=True, description="Verify token expiration")
    verify_aud: bool = Field(default=True, description="Verify audience claim")
    verify_iss: bool = Field(default=True, description="Verify issuer claim")
    leeway: int = Field(
        default=0, description="Time leeway in seconds for token validation"
    )
    cache_jwks: bool = Field(default=True, description="Cache JWKS keys")
    jwks_cache_ttl: int = Field(default=3600, description="JWKS cache TTL in seconds")

    @field_validator("issuer")
    @classmethod
    def validate_issuer(cls, v: str) -> str:
        """Ensure issuer URL doesn't end with a slash."""
        return v.rstrip("/")


class OIDCProvider:
    """
    OIDC provider client for token validation and introspection.

    This class handles communication with OIDC-compliant identity providers,
    including fetching JWKS keys, introspecting tokens, and performing
    discovery of OIDC endpoints.

    Example:
        ```python
        provider = OIDCProvider(config)
        await provider.initialize()

        # Validate a JWT token
        user_info = await provider.validate_token(token)
        ```
    """

    def __init__(self, config: OIDCConfig):
        """
        Initialize OIDC provider.

        Args:
            config: OIDC configuration
        """
        self.config = config
        self._jwks: Optional[Dict[str, Any]] = None
        self._jwks_cache_time: Optional[datetime] = None
        self._well_known_config: Optional[Dict[str, Any]] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """
        Initialize the OIDC provider by discovering endpoints.

        This method fetches the OIDC configuration from the well-known
        endpoint and sets up the necessary URIs.
        """
        self._client = httpx.AsyncClient(timeout=30.0)

        try:
            # Discover OIDC configuration
            await self._discover_configuration()

            # Fetch JWKS if not using introspection
            if self.config.cache_jwks:
                await self._fetch_jwks()

            logger.info(f"OIDC provider initialized: {self.config.issuer}")

        except Exception as e:
            logger.error(f"Failed to initialize OIDC provider: {e}")
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    async def _discover_configuration(self) -> None:
        """
        Discover OIDC configuration from well-known endpoint.

        This implements the OIDC Discovery specification:
        https://openid.net/specs/openid-connect-discovery-1_0.html
        """
        well_known_url = f"{self.config.issuer}/.well-known/openid-configuration"

        try:
            response = await self._client.get(well_known_url)
            response.raise_for_status()
            self._well_known_config = response.json()

            # Set discovered endpoints if not explicitly configured
            if not self.config.jwks_uri:
                self.config.jwks_uri = self._well_known_config.get("jwks_uri")

            if not self.config.token_introspection_uri:
                self.config.token_introspection_uri = self._well_known_config.get(
                    "introspection_endpoint"
                )

            logger.debug(f"OIDC configuration discovered from {well_known_url}")

        except httpx.HTTPError as e:
            logger.error(f"Failed to discover OIDC configuration: {e}")
            raise ValueError(
                f"Could not discover OIDC configuration from {well_known_url}. "
                "Ensure the issuer URL is correct and the provider is accessible."
            )

    async def _fetch_jwks(self, force: bool = False) -> Dict[str, Any]:
        """
        Fetch JWKS (JSON Web Key Set) from the provider.

        Args:
            force: Force refresh even if cached

        Returns:
            JWKS dictionary
        """
        # Check cache
        if (
            not force
            and self._jwks
            and self._jwks_cache_time
            and self.config.cache_jwks
        ):
            age = (datetime.now() - self._jwks_cache_time).total_seconds()
            if age < self.config.jwks_cache_ttl:
                return self._jwks

        if not self.config.jwks_uri:
            raise ValueError("JWKS URI not configured or discovered")

        try:
            response = await self._client.get(self.config.jwks_uri)
            response.raise_for_status()
            self._jwks = response.json()
            self._jwks_cache_time = datetime.now()

            logger.debug(f"JWKS fetched from {self.config.jwks_uri}")
            return self._jwks

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise ValueError(f"Could not fetch JWKS from {self.config.jwks_uri}")

    async def get_jwks(self) -> Dict[str, Any]:
        """
        Get JWKS, fetching if necessary.

        Returns:
            JWKS dictionary
        """
        if not self._jwks:
            await self._fetch_jwks()
        return self._jwks

    async def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect a token using the OIDC introspection endpoint.

        This is useful for opaque tokens or as a fallback for JWT validation.

        Args:
            token: The access token to introspect

        Returns:
            Token introspection response

        Raises:
            ValueError: If introspection endpoint is not configured
            httpx.HTTPError: If introspection request fails
        """
        if not self.config.token_introspection_uri:
            raise ValueError("Token introspection endpoint not configured")

        if not self.config.client_secret:
            raise ValueError("Client secret required for token introspection")

        try:
            response = await self._client.post(
                self.config.token_introspection_uri,
                auth=(self.config.client_id, self.config.client_secret),
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("active"):
                raise ValueError("Token is not active")

            return result

        except httpx.HTTPError as e:
            logger.error(f"Token introspection failed: {e}")
            raise

    def get_issuer(self) -> str:
        """Get the configured issuer."""
        return self.config.issuer

    def get_algorithms(self) -> List[str]:
        """Get allowed algorithms."""
        return self.config.algorithms

    def get_audience(self) -> Optional[str]:
        """Get expected audience."""
        return self.config.audience
