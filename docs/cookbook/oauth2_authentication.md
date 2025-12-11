# OAuth2/OIDC Authentication with HealthChain

This guide demonstrates how to secure your HealthChain API with OAuth2 and OpenID Connect (OIDC) authentication using industry-standard identity providers like Keycloak, Auth0, or Okta.

## Overview

HealthChain provides built-in support for:

- **JWT Token Validation**: Validate JWT tokens using JWKS or token introspection
- **OIDC Integration**: Support for any OIDC-compliant identity provider
- **Role-Based Access Control (RBAC)**: Protect endpoints with role requirements
- **Scope-Based Authorization**: OAuth2 scope validation for fine-grained access
- **Keycloak Reference Implementation**: Example with Keycloak as authorization server

## Quick Start

### 1. Install Dependencies

The authentication module requires additional dependencies:

```bash
pip install pyjwt[crypto] cryptography
```

### 2. Basic Setup

```python
from healthchain.gateway.api.app import HealthChainAPI
from healthchain.gateway.api.auth import (
    JWTAuthMiddleware,
    OIDCConfig,
    OIDCProvider,
)

# Create API
app = HealthChainAPI()

# Configure OIDC provider
oidc_config = OIDCConfig(
    issuer="https://your-keycloak.com/realms/healthchain",
    client_id="healthchain-api",
    client_secret="your-secret",
    audience="healthchain-api"
)

# Initialize and add authentication
async def setup_auth():
    oidc_provider = OIDCProvider(oidc_config)
    await oidc_provider.initialize()

    app.add_middleware(
        JWTAuthMiddleware,
        oidc_provider=oidc_provider,
        exclude_paths=["/docs", "/health"]
    )
```

## Keycloak Setup

### Step 1: Install Keycloak

Using Docker:

```bash
docker run -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:latest start-dev
```

### Step 2: Create Realm

1. Access Keycloak at http://localhost:8080
2. Login with admin credentials
3. Create a new realm called "healthchain"

### Step 3: Create Client

1. Navigate to Clients → Create client
2. Client ID: `healthchain-api`
3. Client authentication: ON
4. Valid redirect URIs: `http://localhost:8000/*`
5. Save and note the client secret from the Credentials tab

### Step 4: Create Roles

1. Navigate to Realm roles → Create role
2. Create roles:
   - `doctor`
   - `nurse`
   - `admin`
   - `healthcare_provider`

### Step 5: Create Users

1. Navigate to Users → Add user
2. Create users and assign roles under Role mapping

### Step 6: Configure HealthChain

```python
from healthchain.gateway.api.auth import OIDCConfig

config = OIDCConfig(
    issuer="http://localhost:8080/realms/healthchain",
    client_id="healthchain-api",
    client_secret="<your-client-secret>",
    audience="healthchain-api"
)
```

## Authentication Patterns

### Pattern 1: Require Authentication

```python
from fastapi import Depends
from healthchain.gateway.api.auth import get_current_user

@app.get("/api/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user}
```

### Pattern 2: Role-Based Access

```python
from healthchain.gateway.api.auth import require_role

@app.get("/api/patients")
async def list_patients(user: dict = Depends(require_role("doctor"))):
    return {"patients": [...]}
```

### Pattern 3: Multiple Roles (OR Logic)

```python
from healthchain.gateway.api.auth import require_roles

@app.get("/api/patient/{id}")
async def get_patient(
    id: int,
    user: dict = Depends(require_roles(["doctor", "nurse"]))
):
    # User needs doctor OR nurse role
    return {"patient": {...}}
```

### Pattern 4: Multiple Roles (AND Logic)

```python
@app.post("/api/admin/audit")
async def create_audit(
    user: dict = Depends(require_roles(["admin", "auditor"], require_all=True))
):
    # User needs both admin AND auditor roles
    return {"status": "created"}
```

### Pattern 5: Scope-Based Access

```python
from healthchain.gateway.api.auth import require_scope

@app.get("/fhir/Patient")
async def search_patients(user: dict = Depends(require_scope("patient/*.read"))):
    return {"resourceType": "Bundle", "entry": [...]}
```

## OIDC Provider Examples

### Keycloak

```python
config = OIDCConfig(
    issuer="https://keycloak.example.com/realms/healthchain",
    client_id="healthchain-api",
    client_secret="your-secret"
)
```

### Auth0

```python
config = OIDCConfig(
    issuer="https://your-tenant.auth0.com",
    client_id="your-client-id",
    client_secret="your-secret",
    audience="https://api.healthchain.example.com"
)
```

### Okta

```python
config = OIDCConfig(
    issuer="https://your-domain.okta.com/oauth2/default",
    client_id="your-client-id",
    client_secret="your-secret"
)
```

### Azure AD

```python
config = OIDCConfig(
    issuer="https://login.microsoftonline.com/{tenant-id}/v2.0",
    client_id="your-client-id",
    client_secret="your-secret"
)
```

## Token Validation Methods

### Method 1: JWKS (Default)

Validates JWT tokens locally using public keys from JWKS endpoint:

```python
app.add_middleware(
    JWTAuthMiddleware,
    oidc_provider=oidc_provider,
    use_introspection=False  # Default
)
```

**Pros**: Fast, no network call per request
**Cons**: Slightly delayed revocation

### Method 2: Token Introspection

Validates tokens by calling the introspection endpoint:

```python
app.add_middleware(
    JWTAuthMiddleware,
    oidc_provider=oidc_provider,
    use_introspection=True
)
```

**Pros**: Real-time revocation
**Cons**: Network call per request

## Middleware Configuration

### Exclude Paths

```python
app.add_middleware(
    JWTAuthMiddleware,
    oidc_provider=oidc_provider,
    exclude_paths=[
        "/",
        "/docs",
        "/openapi.json",
        "/health",
        "/public/*"  # Wildcard support
    ]
)
```

### Optional Authentication

```python
app.add_middleware(
    JWTAuthMiddleware,
    oidc_provider=oidc_provider,
    optional_auth_paths=[
        "/api/public/*"  # Auth optional, user extracted if present
    ]
)
```

## Testing

### Get Token from Keycloak

```bash
curl -X POST http://localhost:8080/realms/healthchain/protocol/openid-connect/token \
  -d 'client_id=healthchain-api' \
  -d 'client_secret=your-secret' \
  -d 'grant_type=password' \
  -d 'username=doctor1' \
  -d 'password=password'
```

### Use Token

```bash
TOKEN="<your-access-token>"

curl http://localhost:8000/api/patients \
  -H "Authorization: Bearer $TOKEN"
```

## User Information Structure

The `user` object contains JWT claims:

```python
{
    "sub": "user-id",
    "preferred_username": "doctor1",
    "email": "doctor1@example.com",
    "email_verified": True,
    "realm_access": {
        "roles": ["doctor", "healthcare_provider"]
    },
    "scope": "openid profile email",
    "exp": 1702389000,
    "iat": 1702388700,
    "iss": "http://localhost:8080/realms/healthchain"
}
```

### Extracting User Info

```python
@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "id": user.get("sub"),
        "username": user.get("preferred_username"),
        "email": user.get("email"),
        "roles": user.get("realm_access", {}).get("roles", [])
    }
```

## Security Best Practices

1. **Use HTTPS in production**: Never use HTTP for authentication
2. **Rotate secrets**: Regularly rotate client secrets
3. **Validate audience**: Always set and verify the `audience` claim
4. **Short token expiration**: Use short-lived access tokens (5-15 minutes)
5. **Use refresh tokens**: For long-lived sessions
6. **Implement rate limiting**: Protect against brute force attacks
7. **Log authentication events**: Monitor for suspicious activity

## Troubleshooting

### Token Validation Fails

1. Check issuer URL matches exactly (no trailing slash)
2. Verify JWKS endpoint is accessible
3. Ensure token hasn't expired
4. Check audience claim matches configuration

### Role Check Fails

1. Verify roles are in the JWT token
2. Check role claim path (realm_access.roles for Keycloak)
3. Ensure user has role assigned in identity provider

### OIDC Discovery Fails

1. Ensure `.well-known/openid-configuration` endpoint is accessible
2. Check network connectivity to identity provider
3. Verify issuer URL is correct

## Complete Example

See the full working example: [cookbook/keycloak_oauth2_integration.py](../../cookbook/keycloak_oauth2_integration.py)

## Related Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenID Connect Specification](https://openid.net/connect/)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
