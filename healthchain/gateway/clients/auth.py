"""
OAuth2 authentication manager for FHIR clients.

This module provides OAuth2 client credentials flow for automatic token
management and refresh.
"""

import logging
import os
import uuid
import asyncio
import threading
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
    key_id: Optional[str] = None  # Key ID (kid) for JWT header - required for JWKS

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
    OAuth2.0 token manager for FHIR clients.

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
        self._refresh_lock = threading.Lock()

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid Bearer access token
        """
        with self._refresh_lock:
            if self._token is None or self._token.is_expired(
                self.refresh_buffer_seconds
            ):
                self._refresh_token()

            return self._token.access_token

    def _refresh_token(self):
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
        with httpx.Client() as client:
            try:
                response = client.post(
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

        # Create and sign JWT with optional kid header
        headers = {"kid": self.config.key_id} if self.config.key_id else None
        signed_jwt = JWT().encode(claims, key, alg="RS384", optional_headers=headers)

        return signed_jwt


class AsyncOAuth2TokenManager:
    """
    Manages OAuth2.0 tokens with automatic refresh for async FHIR clients.

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
        self._refresh_lock: Optional[asyncio.Lock] = None

    def _get_refresh_lock(self) -> asyncio.Lock:
        """Get or create the refresh lock when an event loop is running."""
        if self._refresh_lock is None:
            # Only create the lock when we have a running event loop
            # This ensures Python 3.9 compatibility
            self._refresh_lock = asyncio.Lock()
        return self._refresh_lock

    async def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid Bearer access token
        """
        async with self._get_refresh_lock():
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

        # Create and sign JWT with optional kid header
        headers = {"kid": self.config.key_id} if self.config.key_id else None
        signed_jwt = JWT().encode(claims, key, alg="RS384", optional_headers=headers)

        return signed_jwt
