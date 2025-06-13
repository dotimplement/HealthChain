"""
OAuth2 authentication manager for FHIR clients.

This module provides OAuth2 client credentials flow for automatic token
management and refresh.
"""

import logging
import os
import uuid
import asyncio
import httpx

from typing import Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class OAuth2Config(BaseModel):
    """OAuth2 configuration for client credentials flow."""

    client_id: str
    token_url: str
    client_secret: Optional[str] = None  # Client secret string for standard flow
    client_secret_path: Optional[str] = (
        None  # Path to private key file for JWT assertion
    )
    scope: Optional[str] = None
    audience: Optional[str] = None  # For Epic and other systems that require audience
    use_jwt_assertion: bool = False  # Use JWT client assertion instead of client secret

    def model_post_init(self, __context) -> None:
        """Validate that exactly one of client_secret or client_secret_path is provided."""
        if not self.client_secret and not self.client_secret_path:
            raise ValueError(
                "Either client_secret or client_secret_path must be provided"
            )

        if self.client_secret and self.client_secret_path:
            raise ValueError("Cannot provide both client_secret and client_secret_path")

        if self.use_jwt_assertion and not self.client_secret_path:
            raise ValueError(
                "use_jwt_assertion=True requires client_secret_path to be set"
            )

        if not self.use_jwt_assertion and self.client_secret_path:
            raise ValueError(
                "client_secret_path can only be used with use_jwt_assertion=True"
            )

    @property
    def secret_value(self) -> str:
        """Get the secret value, reading from file if necessary."""
        if self.client_secret_path:
            try:
                with open(self.client_secret_path, "rb") as f:
                    return f.read().decode("utf-8")
            except Exception as e:
                raise ValueError(
                    f"Failed to read secret from {self.client_secret_path}: {e}"
                )
        return self.client_secret


class TokenInfo(BaseModel):
    """Token information with expiry tracking."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None
    expires_at: datetime

    @classmethod
    def from_response(cls, response_data: Dict[str, Any]) -> "TokenInfo":
        """Create TokenInfo from OAuth2.0 token response."""
        expires_at = datetime.now() + timedelta(
            seconds=response_data.get("expires_in", 3600)
        )

        return cls(
            access_token=response_data["access_token"],
            token_type=response_data.get("token_type", "Bearer"),
            expires_in=response_data.get("expires_in", 3600),
            scope=response_data.get("scope"),
            expires_at=expires_at,
        )

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired or will expire within buffer time."""
        return datetime.now() + timedelta(seconds=buffer_seconds) >= self.expires_at


class OAuth2TokenManager:
    """
    Manages OAuth2.0 tokens with automatic refresh for FHIR clients.

    Supports client credentials flow commonly used in healthcare integrations.
    """

    def __init__(self, config: OAuth2Config, refresh_buffer_seconds: int = 300):
        """
        Initialize OAuth2 token manager.

        Args:
            config: OAuth2 configuration
            refresh_buffer_seconds: Refresh token this many seconds before expiry
        """
        self.config = config
        self.refresh_buffer_seconds = refresh_buffer_seconds
        self._token: Optional[TokenInfo] = None
        self._refresh_lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid Bearer access token
        """
        async with self._refresh_lock:
            if self._token is None or self._token.is_expired(
                self.refresh_buffer_seconds
            ):
                await self._refresh_token()

            return self._token.access_token

    async def _refresh_token(self):
        """Refresh the access token using client credentials flow."""
        logger.debug(f"Refreshing token from {self.config.token_url}")

        # Check if client_secret is a private key path or JWT assertion is enabled
        if self.config.use_jwt_assertion or self.config.client_secret_path:
            # Use JWT client assertion flow (Epic/SMART on FHIR style)
            jwt_assertion = self._create_jwt_assertion()
            token_data = {
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": jwt_assertion,
            }
        else:
            # Standard client credentials flow
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.secret_value,
            }

        if self.config.scope:
            token_data["scope"] = self.config.scope

        if self.config.audience:
            token_data["audience"] = self.config.audience

        # Make token request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30,
                )
                response.raise_for_status()

                response_data = response.json()
                self._token = TokenInfo.from_response(response_data)

                logger.debug(
                    f"Token refreshed successfully, expires at {self._token.expires_at}"
                )

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Token refresh failed: {e.response.status_code} {e.response.text}"
                )
                raise Exception(f"Failed to refresh token: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Token refresh error: {str(e)}")
                raise

    def invalidate_token(self):
        """Invalidate the current token to force refresh on next request."""
        self._token = None

    def _create_jwt_assertion(self) -> str:
        """Create JWT client assertion for SMART on FHIR authentication."""
        from jwt import JWT, jwk_from_pem

        # Generate unique JTI
        jti = str(uuid.uuid4())

        # Load private key (client_secret should be path to private key for JWT assertion)
        try:
            with open(self.config.client_secret_path, "rb") as f:
                private_key_data = f.read()
            key = jwk_from_pem(private_key_data)
        except Exception as e:
            raise Exception(
                f"Failed to load private key from {os.path.basename(self.config.client_secret_path)}: {e}"
            )

        # Create JWT claims matching the script
        now = datetime.now(timezone.utc)
        claims = {
            "iss": self.config.client_id,  # Issuer (client ID)
            "sub": self.config.client_id,  # Subject (client ID)
            "aud": self.config.token_url,  # Audience (token endpoint)
            "jti": jti,  # Unique token identifier
            "iat": int(now.timestamp()),  # Issued at
            "exp": int(
                (now + timedelta(minutes=5)).timestamp()
            ),  # Expires in 5 minutes
        }

        # Create and sign JWT
        signed_jwt = JWT().encode(claims, key, alg="RS384")

        return signed_jwt


class FHIRAuthConfig(BaseModel):
    """Configuration for FHIR server authentication."""

    # OAuth2 settings
    client_id: str
    client_secret: Optional[str] = None  # Client secret string for standard flow
    client_secret_path: Optional[str] = (
        None  # Path to private key file for JWT assertion
    )
    token_url: str
    scope: Optional[str] = "system/*.read system/*.write"
    audience: Optional[str] = None
    use_jwt_assertion: bool = False  # Use JWT client assertion (Epic/SMART style)

    # Connection settings
    base_url: str
    timeout: int = 30
    verify_ssl: bool = True

    def model_post_init(self, __context) -> None:
        """Validate that exactly one of client_secret or client_secret_path is provided."""
        if not self.client_secret and not self.client_secret_path:
            raise ValueError(
                "Either client_secret or client_secret_path must be provided"
            )

        if self.client_secret and self.client_secret_path:
            raise ValueError("Cannot provide both client_secret and client_secret_path")

        if self.use_jwt_assertion and not self.client_secret_path:
            raise ValueError(
                "use_jwt_assertion=True requires client_secret_path to be set"
            )

        if not self.use_jwt_assertion and self.client_secret_path:
            raise ValueError(
                "client_secret_path can only be used with use_jwt_assertion=True"
            )

    def to_oauth2_config(self) -> OAuth2Config:
        """Convert to OAuth2Config for token manager."""
        return OAuth2Config(
            client_id=self.client_id,
            client_secret=self.client_secret,
            client_secret_path=self.client_secret_path,
            token_url=self.token_url,
            scope=self.scope,
            audience=self.audience,
            use_jwt_assertion=self.use_jwt_assertion,
        )

    @classmethod
    def from_env(cls, env_prefix: str) -> "FHIRAuthConfig":
        """
        Create FHIRAuthConfig from environment variables.

        Args:
            env_prefix: Environment variable prefix (e.g., "EPIC")

        Expected environment variables:
            {env_prefix}_CLIENT_ID
            {env_prefix}_CLIENT_SECRET (or {env_prefix}_CLIENT_SECRET_PATH)
            {env_prefix}_TOKEN_URL
            {env_prefix}_BASE_URL
            {env_prefix}_SCOPE (optional)
            {env_prefix}_AUDIENCE (optional)
            {env_prefix}_TIMEOUT (optional, default: 30)
            {env_prefix}_VERIFY_SSL (optional, default: true)
            {env_prefix}_USE_JWT_ASSERTION (optional, default: false)

        Returns:
            FHIRAuthConfig instance

        Example:
            # Set environment variables:
            # EPIC_CLIENT_ID=app123
            # EPIC_CLIENT_SECRET=secret456
            # EPIC_TOKEN_URL=https://epic.com/oauth2/token
            # EPIC_BASE_URL=https://epic.com/api/FHIR/R4

            config = FHIRAuthConfig.from_env("EPIC")
        """
        import os

        # Read required environment variables
        client_id = os.getenv(f"{env_prefix}_CLIENT_ID")
        client_secret = os.getenv(f"{env_prefix}_CLIENT_SECRET")
        client_secret_path = os.getenv(f"{env_prefix}_CLIENT_SECRET_PATH")
        token_url = os.getenv(f"{env_prefix}_TOKEN_URL")
        base_url = os.getenv(f"{env_prefix}_BASE_URL")

        if not all([client_id, token_url, base_url]):
            missing = [
                var
                for var, val in [
                    (f"{env_prefix}_CLIENT_ID", client_id),
                    (f"{env_prefix}_TOKEN_URL", token_url),
                    (f"{env_prefix}_BASE_URL", base_url),
                ]
                if not val
            ]
            raise ValueError(f"Missing required environment variables: {missing}")

        # Read optional environment variables
        scope = os.getenv(f"{env_prefix}_SCOPE", "system/*.read system/*.write")
        audience = os.getenv(f"{env_prefix}_AUDIENCE")
        timeout = int(os.getenv(f"{env_prefix}_TIMEOUT", "30"))
        verify_ssl = os.getenv(f"{env_prefix}_VERIFY_SSL", "true").lower() == "true"
        use_jwt_assertion = (
            os.getenv(f"{env_prefix}_USE_JWT_ASSERTION", "false").lower() == "true"
        )

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            client_secret_path=client_secret_path,
            token_url=token_url,
            base_url=base_url,
            scope=scope,
            audience=audience,
            timeout=timeout,
            verify_ssl=verify_ssl,
            use_jwt_assertion=use_jwt_assertion,
        )

    def to_connection_string(self) -> str:
        """
        Convert FHIRAuthConfig to connection string format.

        Returns:
            Connection string in fhir:// format

        Example:
            config = FHIRAuthConfig(...)
            connection_string = config.to_connection_string()
            # Returns: "fhir://hostname/path?client_id=...&token_url=..."
        """
        # Extract hostname and path from base_url
        import urllib.parse

        parsed_base = urllib.parse.urlparse(self.base_url)

        # Build query parameters
        params = {
            "client_id": self.client_id,
            "token_url": self.token_url,
        }

        # Add secret (either client_secret or client_secret_path)
        if self.client_secret:
            params["client_secret"] = self.client_secret
        elif self.client_secret_path:
            params["client_secret_path"] = self.client_secret_path

        # Add optional parameters
        if self.scope:
            params["scope"] = self.scope
        if self.audience:
            params["audience"] = self.audience
        if self.timeout != 30:
            params["timeout"] = str(self.timeout)
        if not self.verify_ssl:
            params["verify_ssl"] = "false"
        if self.use_jwt_assertion:
            params["use_jwt_assertion"] = "true"

        # Build connection string
        query_string = urllib.parse.urlencode(params)
        return f"fhir://{parsed_base.netloc}{parsed_base.path}?{query_string}"


def parse_fhir_auth_connection_string(connection_string: str) -> FHIRAuthConfig:
    """
    Parse a FHIR connection string into authentication configuration.

    Format: fhir://hostname:port/path?client_id=xxx&client_secret=xxx&token_url=xxx&scope=xxx
    Or for JWT: fhir://hostname:port/path?client_id=xxx&client_secret_path=xxx&token_url=xxx&use_jwt_assertion=true

    Args:
        connection_string: FHIR connection string with OAuth2 credentials

    Returns:
        FHIRAuthConfig with parsed settings

    Raises:
        ValueError: If connection string is invalid or missing required parameters
    """
    import urllib.parse

    if not connection_string.startswith("fhir://"):
        raise ValueError("Connection string must start with fhir://")

    parsed = urllib.parse.urlparse(connection_string)
    params = dict(urllib.parse.parse_qsl(parsed.query))

    # Validate required parameters
    required_params = ["client_id", "token_url"]
    missing_params = [param for param in required_params if param not in params]

    if missing_params:
        raise ValueError(f"Missing required parameters: {missing_params}")

    # Check that exactly one of client_secret or client_secret_path is provided
    has_secret = "client_secret" in params
    has_secret_path = "client_secret_path" in params

    if not has_secret and not has_secret_path:
        raise ValueError(
            "Either 'client_secret' or 'client_secret_path' parameter must be provided"
        )

    if has_secret and has_secret_path:
        raise ValueError(
            "Cannot provide both 'client_secret' and 'client_secret_path' parameters"
        )

    # Build base URL
    base_url = f"https://{parsed.netloc}{parsed.path}"

    return FHIRAuthConfig(
        client_id=params["client_id"],
        client_secret=params.get("client_secret"),
        client_secret_path=params.get("client_secret_path"),
        token_url=params["token_url"],
        scope=params.get("scope", "system/*.read system/*.write"),
        audience=params.get("audience"),
        base_url=base_url,
        timeout=int(params.get("timeout", 30)),
        verify_ssl=params.get("verify_ssl", "true").lower() == "true",
        use_jwt_assertion=params.get("use_jwt_assertion", "false").lower() == "true",
    )
