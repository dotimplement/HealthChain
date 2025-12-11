"""
JWT authentication middleware for FastAPI.

Provides token validation, user extraction, and request authentication.
"""

import logging
from typing import Optional, Callable, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import jwt

try:
    from jwt import PyJWKClient
except ImportError:
    # PyJWKClient is available in PyJWT 2.0+
    PyJWKClient = None

from healthchain.gateway.api.auth.oidc import OIDCProvider

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for JWT token validation.

    This middleware validates JWT tokens on incoming requests and attaches
    user information to the request state. It supports OIDC-compliant
    providers and can validate tokens using JWKS or token introspection.

    Example:
        ```python
        from healthchain.gateway.api.auth import JWTAuthMiddleware, OIDCConfig

        oidc_config = OIDCConfig(
            issuer="https://keycloak.example.com/realms/healthchain",
            client_id="healthchain-api",
            audience="healthchain-api"
        )

        app.add_middleware(
            JWTAuthMiddleware,
            oidc_config=oidc_config,
            exclude_paths=["/docs", "/openapi.json", "/health"]
        )
        ```
    """

    def __init__(
        self,
        app,
        oidc_provider: Optional[OIDCProvider] = None,
        exclude_paths: Optional[List[str]] = None,
        optional_auth_paths: Optional[List[str]] = None,
        use_introspection: bool = False,
    ):
        """
        Initialize JWT authentication middleware.

        Args:
            app: FastAPI application instance
            oidc_provider: Initialized OIDC provider instance
            exclude_paths: List of paths to exclude from authentication
            optional_auth_paths: List of paths where auth is optional
            use_introspection: Use token introspection instead of local JWT validation
        """
        super().__init__(app)
        self.oidc_provider = oidc_provider
        self.exclude_paths = set(exclude_paths or [])
        self.optional_auth_paths = set(optional_auth_paths or [])
        self.use_introspection = use_introspection
        self._jwks_client = None  # Will be initialized as PyJWKClient if available

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and validate JWT token if present.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response from the next handler
        """
        # Check if path is excluded
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Check if authentication is optional for this path
        optional = self._is_optional_auth_path(request.url.path)

        try:
            # Extract token from request
            token = self._extract_token(request)

            if not token:
                if optional:
                    # Continue without authentication
                    request.state.user = None
                    return await call_next(request)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Missing authentication token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            # Validate token and extract user info
            user_info = await self._validate_token(token)

            # Attach user info to request state
            request.state.user = user_info

            # Continue processing
            response = await call_next(request)
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            if optional:
                request.state.user = None
                return await call_next(request)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if the path is excluded from authentication.

        Args:
            path: Request path

        Returns:
            True if path is excluded
        """
        # Exact match
        if path in self.exclude_paths:
            return True

        # Prefix match (for paths ending with *)
        for excluded in self.exclude_paths:
            if excluded.endswith("*") and path.startswith(excluded[:-1]):
                return True

        return False

    def _is_optional_auth_path(self, path: str) -> bool:
        """
        Check if authentication is optional for this path.

        Args:
            path: Request path

        Returns:
            True if authentication is optional
        """
        if path in self.optional_auth_paths:
            return True

        for optional in self.optional_auth_paths:
            if optional.endswith("*") and path.startswith(optional[:-1]):
                return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header.

        Args:
            request: The incoming request

        Returns:
            Token string or None if not found
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    async def _validate_token(self, token: str) -> dict:
        """
        Validate JWT token and extract user information.

        Args:
            token: JWT token string

        Returns:
            Dictionary containing user information

        Raises:
            HTTPException: If token is invalid
        """
        if not self.oidc_provider:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OIDC provider not configured",
            )

        try:
            if self.use_introspection:
                # Use token introspection
                user_info = await self.oidc_provider.introspect_token(token)
            else:
                # Validate JWT locally
                user_info = await self._validate_jwt(token)

            return user_info

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def _validate_jwt(self, token: str) -> dict:
        """
        Validate JWT token locally using JWKS.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload
        """
        config = self.oidc_provider.config

        # Initialize JWKS client if needed and available
        if not self._jwks_client and config.jwks_uri and PyJWKClient is not None:
            self._jwks_client = PyJWKClient(config.jwks_uri)

        # Get signing key
        if self._jwks_client:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key
        else:
            # Fallback to fetching JWKS manually
            jwks = await self.oidc_provider.get_jwks()
            # This is a simplified approach; in production you'd need to
            # match the key ID from the token header
            key = jwks

        # Decode and validate token
        payload = jwt.decode(
            token,
            key,
            algorithms=config.algorithms,
            audience=config.audience if config.verify_aud else None,
            issuer=config.issuer if config.verify_iss else None,
            options={
                "verify_exp": config.verify_exp,
                "verify_aud": config.verify_aud,
                "verify_iss": config.verify_iss,
            },
            leeway=config.leeway,
        )

        return payload
