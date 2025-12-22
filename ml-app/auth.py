"""
OAuth2 JWT Bearer Authentication Module

Provides OAuth2 JWT token validation for securing API endpoints.
Supports standard JWKS-based token verification for production deployments.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)


@dataclass
class UserClaims:
    """Validated user claims from JWT token."""
    sub: str  # Subject (user ID)
    iss: str  # Issuer
    aud: str  # Audience
    exp: int  # Expiration
    iat: int  # Issued at
    scope: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    roles: Optional[list] = None

    @classmethod
    def from_payload(cls, payload: dict) -> "UserClaims":
        """Create UserClaims from JWT payload."""
        return cls(
            sub=payload.get("sub", ""),
            iss=payload.get("iss", ""),
            aud=payload.get("aud", ""),
            exp=payload.get("exp", 0),
            iat=payload.get("iat", 0),
            scope=payload.get("scope"),
            email=payload.get("email"),
            name=payload.get("name"),
            roles=payload.get("roles", [])
        )


class JWKSClient:
    """Client for fetching and caching JWKS (JSON Web Key Set)."""

    def __init__(self, jwks_uri: str, cache_ttl: int = 3600):
        self.jwks_uri = jwks_uri
        self.cache_ttl = cache_ttl
        self._jwks_cache = None
        self._cache_time = 0

    async def get_signing_key(self, kid: str) -> dict:
        """Get signing key by key ID from JWKS."""
        import time

        current_time = time.time()

        # Refresh cache if expired
        if self._jwks_cache is None or (current_time - self._cache_time) > self.cache_ttl:
            await self._refresh_jwks()

        # Find key by kid
        for key in self._jwks_cache.get("keys", []):
            if key.get("kid") == kid:
                return key

        # Key not found, try refreshing once
        await self._refresh_jwks()
        for key in self._jwks_cache.get("keys", []):
            if key.get("kid") == kid:
                return key

        raise ValueError(f"Key with kid '{kid}' not found in JWKS")

    async def _refresh_jwks(self):
        """Fetch JWKS from endpoint."""
        import time

        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._cache_time = time.time()
            logger.debug(f"Refreshed JWKS from {self.jwks_uri}")


class OAuth2JWTBearer(HTTPBearer):
    """
    OAuth2 JWT Bearer token authentication.

    Validates JWT tokens using JWKS for signature verification.
    Supports RS256 and other asymmetric algorithms.
    """

    def __init__(
        self,
        settings,
        auto_error: bool = True
    ):
        super().__init__(auto_error=auto_error)
        self.settings = settings
        self.jwks_client = None

        if settings.oauth2_jwks_uri:
            self.jwks_client = JWKSClient(settings.oauth2_jwks_uri)

    async def __call__(self, request: Request) -> Optional[UserClaims]:
        """Validate JWT token and return user claims."""
        if not self.settings.oauth2_enabled:
            return None

        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if credentials is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None

        token = credentials.credentials

        try:
            payload = await self._verify_token(token)
            return UserClaims.from_payload(payload)
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {str(e)}",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None

    async def _verify_token(self, token: str) -> dict:
        """Verify JWT token and return payload."""
        try:
            from jose import jwt, JWTError
        except ImportError:
            raise ImportError(
                "python-jose is required for JWT verification. "
                "Install with: pip install python-jose[cryptography]"
            )

        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise ValueError("Token header missing 'kid' claim")

        # Get signing key from JWKS
        if not self.jwks_client:
            raise ValueError("JWKS client not configured")

        signing_key = await self.jwks_client.get_signing_key(kid)

        # Build public key from JWK
        from jose.backends import RSAKey
        public_key = RSAKey(signing_key, algorithm=unverified_header.get("alg", "RS256"))

        # Verify and decode token
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_aud": self.settings.oauth2_audience is not None,
            "verify_iss": self.settings.oauth2_issuer is not None
        }

        payload = jwt.decode(
            token,
            public_key.to_pem().decode("utf-8"),
            algorithms=self.settings.algorithms_list,
            audience=self.settings.oauth2_audience,
            issuer=self.settings.oauth2_issuer,
            options=options
        )

        return payload


async def get_current_user(
    request: Request,
) -> Optional[UserClaims]:
    """
    Dependency to get current authenticated user.

    Returns None if OAuth2 is disabled or no token provided.
    Raises HTTPException if token is invalid.
    """
    from config import get_settings

    settings = get_settings()

    if not settings.oauth2_enabled:
        return None

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    oauth2_scheme = OAuth2JWTBearer(settings, auto_error=False)
    return await oauth2_scheme(request)


def require_auth(
    user: Optional[UserClaims] = Depends(get_current_user)
) -> UserClaims:
    """
    Dependency that requires authentication.

    Use this dependency when an endpoint must be authenticated.
    """
    from config import get_settings

    settings = get_settings()

    if not settings.oauth2_enabled:
        # Return a placeholder user when auth is disabled
        return UserClaims(
            sub="anonymous",
            iss="local",
            aud="ml-healthcare-api",
            exp=0,
            iat=0
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def require_scope(required_scope: str):
    """
    Create a dependency that requires a specific OAuth2 scope.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_scope("admin"))])
        async def admin_endpoint():
            ...
    """
    def scope_checker(user: UserClaims = Depends(require_auth)) -> UserClaims:
        if user.scope and required_scope in user.scope.split():
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scope '{required_scope}' required"
        )

    return scope_checker


def require_role(required_role: str):
    """
    Create a dependency that requires a specific role.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint():
            ...
    """
    def role_checker(user: UserClaims = Depends(require_auth)) -> UserClaims:
        if user.roles and required_role in user.roles:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{required_role}' required"
        )

    return role_checker
