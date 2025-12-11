"""
FastAPI dependencies for authentication and authorization.

Provides reusable dependency functions for protecting endpoints
with role-based access control.
"""

import logging
from typing import List, Optional, Set
from fastapi import Depends, HTTPException, Request, status

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[dict]:
    """
    Get the current authenticated user from request state.

    This dependency extracts user information that was attached to the
    request state by the JWT authentication middleware.

    Args:
        request: The incoming request

    Returns:
        User information dictionary or None if not authenticated

    Example:
        ```python
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user": user}
        ```
    """
    return getattr(request.state, "user", None)


async def require_authenticated_user(
    user: Optional[dict] = Depends(get_current_user),
) -> dict:
    """
    Require an authenticated user.

    This dependency ensures that a valid authenticated user is present,
    raising an HTTP 401 error if not.

    Args:
        user: User information from get_current_user dependency

    Returns:
        User information dictionary

    Raises:
        HTTPException: 401 if user is not authenticated

    Example:
        ```python
        @app.get("/protected")
        async def protected_route(user: dict = Depends(require_authenticated_user)):
            return {"user_id": user.get("sub")}
        ```
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(required_role: str):
    """
    Create a dependency that requires a specific role.

    This factory function creates a FastAPI dependency that checks if the
    authenticated user has the required role. Roles are typically extracted
    from JWT claims like 'realm_access.roles' (Keycloak) or 'roles' (Auth0).

    Args:
        required_role: The role name required to access the endpoint

    Returns:
        FastAPI dependency function

    Example:
        ```python
        @app.get("/admin")
        async def admin_route(user: dict = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
        ```
    """

    async def role_checker(user: dict = Depends(require_authenticated_user)) -> dict:
        roles = _extract_roles(user)

        if required_role not in roles:
            logger.warning(
                f"User {user.get('sub')} attempted to access resource requiring "
                f"role '{required_role}' but only has roles: {roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )

        return user

    return role_checker


def require_roles(required_roles: List[str], require_all: bool = False):
    """
    Create a dependency that requires multiple roles.

    This factory function creates a FastAPI dependency that checks if the
    authenticated user has the required roles. Can check for any role
    (OR logic) or all roles (AND logic).

    Args:
        required_roles: List of role names
        require_all: If True, user must have all roles. If False, any role is sufficient.

    Returns:
        FastAPI dependency function

    Example:
        ```python
        # User must have at least one of these roles
        @app.get("/healthcare")
        async def healthcare_route(
            user: dict = Depends(require_roles(["doctor", "nurse"]))
        ):
            return {"message": "Healthcare access granted"}

        # User must have both roles
        @app.get("/admin-healthcare")
        async def admin_healthcare_route(
            user: dict = Depends(require_roles(["admin", "doctor"], require_all=True))
        ):
            return {"message": "Admin healthcare access granted"}
        ```
    """

    async def roles_checker(user: dict = Depends(require_authenticated_user)) -> dict:
        user_roles = _extract_roles(user)

        if require_all:
            # User must have ALL required roles
            missing_roles = set(required_roles) - user_roles
            if missing_roles:
                logger.warning(
                    f"User {user.get('sub')} missing required roles: {missing_roles}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"All roles required: {required_roles}",
                )
        else:
            # User must have at least ONE required role
            if not any(role in user_roles for role in required_roles):
                logger.warning(
                    f"User {user.get('sub')} has no matching roles. "
                    f"Required: {required_roles}, Has: {user_roles}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of these roles required: {required_roles}",
                )

        return user

    return roles_checker


def require_scope(required_scope: str):
    """
    Create a dependency that requires a specific OAuth2 scope.

    This factory function creates a FastAPI dependency that checks if the
    access token has the required OAuth2 scope.

    Args:
        required_scope: The scope required to access the endpoint

    Returns:
        FastAPI dependency function

    Example:
        ```python
        @app.get("/patient/read")
        async def read_patient(user: dict = Depends(require_scope("patient:read"))):
            return {"message": "Patient read access granted"}
        ```
    """

    async def scope_checker(user: dict = Depends(require_authenticated_user)) -> dict:
        scopes = _extract_scopes(user)

        if required_scope not in scopes:
            logger.warning(
                f"User {user.get('sub')} attempted to access resource requiring "
                f"scope '{required_scope}' but only has scopes: {scopes}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required_scope}' required",
            )

        return user

    return scope_checker


def require_scopes(required_scopes: List[str], require_all: bool = True):
    """
    Create a dependency that requires multiple OAuth2 scopes.

    Args:
        required_scopes: List of scope names
        require_all: If True, token must have all scopes. If False, any scope is sufficient.

    Returns:
        FastAPI dependency function

    Example:
        ```python
        @app.post("/patient/write")
        async def write_patient(
            user: dict = Depends(require_scopes(["patient:read", "patient:write"], require_all=True))
        ):
            return {"message": "Patient write access granted"}
        ```
    """

    async def scopes_checker(user: dict = Depends(require_authenticated_user)) -> dict:
        user_scopes = _extract_scopes(user)

        if require_all:
            missing_scopes = set(required_scopes) - user_scopes
            if missing_scopes:
                logger.warning(
                    f"User {user.get('sub')} missing required scopes: {missing_scopes}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"All scopes required: {required_scopes}",
                )
        else:
            if not any(scope in user_scopes for scope in required_scopes):
                logger.warning(
                    f"User {user.get('sub')} has no matching scopes. "
                    f"Required: {required_scopes}, Has: {user_scopes}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of these scopes required: {required_scopes}",
                )

        return user

    return scopes_checker


def _extract_roles(user: dict) -> Set[str]:
    """
    Extract roles from user token claims.

    Supports multiple common role claim formats:
    - Keycloak: realm_access.roles, resource_access.<client>.roles
    - Auth0: roles or permissions
    - Generic: roles

    Args:
        user: User information dictionary from JWT token

    Returns:
        Set of role names
    """
    roles = set()

    # Standard 'roles' claim
    if "roles" in user:
        if isinstance(user["roles"], list):
            roles.update(user["roles"])
        elif isinstance(user["roles"], str):
            roles.add(user["roles"])

    # Keycloak realm_access.roles
    if "realm_access" in user and isinstance(user["realm_access"], dict):
        realm_roles = user["realm_access"].get("roles", [])
        if isinstance(realm_roles, list):
            roles.update(realm_roles)

    # Keycloak resource_access.<client>.roles
    if "resource_access" in user and isinstance(user["resource_access"], dict):
        for client, access in user["resource_access"].items():
            if isinstance(access, dict) and "roles" in access:
                client_roles = access["roles"]
                if isinstance(client_roles, list):
                    roles.update(client_roles)

    # Auth0 permissions as roles
    if "permissions" in user:
        if isinstance(user["permissions"], list):
            roles.update(user["permissions"])

    return roles


def _extract_scopes(user: dict) -> Set[str]:
    """
    Extract OAuth2 scopes from user token claims.

    Args:
        user: User information dictionary from JWT token

    Returns:
        Set of scope names
    """
    scopes = set()

    # Standard 'scope' claim (space-separated string)
    if "scope" in user:
        if isinstance(user["scope"], str):
            scopes.update(user["scope"].split())
        elif isinstance(user["scope"], list):
            scopes.update(user["scope"])

    # Alternative 'scopes' claim
    if "scopes" in user:
        if isinstance(user["scopes"], list):
            scopes.update(user["scopes"])
        elif isinstance(user["scopes"], str):
            scopes.update(user["scopes"].split())

    return scopes
