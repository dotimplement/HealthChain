# Authentication & Authorization Module

This module provides OAuth2/OIDC authentication and role-based access control for HealthChain API.

## Features

- **JWT Token Validation**: Validate JWT tokens using JWKS endpoints
- **OIDC Integration**: Support for Keycloak, Auth0, Okta, Azure AD, and other OIDC providers
- **Token Introspection**: Alternative validation using OAuth2 introspection
- **Role-Based Access Control**: Protect endpoints with role requirements
- **Scope Validation**: OAuth2 scope-based authorization
- **Flexible Middleware**: Path-based exclusions and optional authentication

## Quick Start

```python
from healthchain.gateway.api.app import HealthChainAPI
from healthchain.gateway.api.auth import (
    JWTAuthMiddleware,
    OIDCConfig,
    OIDCProvider,
    require_role,
)

# Configure OIDC
config = OIDCConfig(
    issuer="https://keycloak.example.com/realms/healthchain",
    client_id="healthchain-api",
    client_secret="your-secret",
    audience="healthchain-api"
)

# Create API
app = HealthChainAPI()

# Setup auth
@app.on_event("startup")
async def setup_auth():
    oidc_provider = OIDCProvider(config)
    await oidc_provider.initialize()

    app.add_middleware(
        JWTAuthMiddleware,
        oidc_provider=oidc_provider,
        exclude_paths=["/docs", "/health"]
    )

# Protect endpoints
@app.get("/api/patients")
async def list_patients(user: dict = Depends(require_role("doctor"))):
    return {"patients": [...]}
```

## Module Structure

- `oidc.py`: OIDC provider configuration and client
- `middleware.py`: JWT authentication middleware
- `dependencies.py`: FastAPI dependencies for RBAC
- `__init__.py`: Public API exports

## Documentation

See the complete guide: [docs/cookbook/oauth2_authentication.md](../../../docs/cookbook/oauth2_authentication.md)

## Example

Working example with Keycloak: [cookbook/keycloak_oauth2_integration.py](../../../cookbook/keycloak_oauth2_integration.py)

## Supported Identity Providers

- Keycloak (reference implementation)
- Auth0
- Okta
- Azure AD
- Google Identity Platform
- Any OIDC-compliant provider

## Dependencies

```bash
pip install pyjwt[crypto] cryptography
```

These are included in HealthChain's main dependencies.
