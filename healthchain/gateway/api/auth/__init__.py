"""
Authentication and authorization module for HealthChain API.

This module provides JWT token validation, OIDC integration,
and role-based access control for securing API endpoints.
"""

from healthchain.gateway.api.auth.middleware import JWTAuthMiddleware
from healthchain.gateway.api.auth.oidc import OIDCConfig, OIDCProvider
from healthchain.gateway.api.auth.dependencies import (
    get_current_user,
    require_role,
    require_roles,
    require_scope,
)

__all__ = [
    "JWTAuthMiddleware",
    "OIDCConfig",
    "OIDCProvider",
    "get_current_user",
    "require_role",
    "require_roles",
    "require_scope",
]
