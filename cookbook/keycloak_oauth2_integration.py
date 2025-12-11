"""
Keycloak OAuth2/OIDC Integration Example for HealthChain API

This example demonstrates how to secure a HealthChain API with Keycloak
authentication and role-based access control.

Prerequisites:
1. Keycloak server running (e.g., http://localhost:8080)
2. A realm configured in Keycloak (e.g., 'healthchain')
3. A client configured in the realm (e.g., 'healthchain-api')
4. Users with appropriate roles created

For Keycloak setup, see: docs/cookbook/setup_keycloak_auth.md
"""

import uvicorn
from fastapi import Depends

from healthchain.gateway.api.app import HealthChainAPI
from healthchain.gateway.api.auth import (
    JWTAuthMiddleware,
    OIDCConfig,
    OIDCProvider,
    get_current_user,
    require_role,
    require_roles,
    require_scope,
)


# Keycloak Configuration
# Replace these values with your Keycloak setup
KEYCLOAK_CONFIG = OIDCConfig(
    issuer="http://localhost:8080/realms/healthchain",
    client_id="healthchain-api",
    client_secret="your-client-secret-here",  # Get from Keycloak client credentials
    audience="healthchain-api",
    algorithms=["RS256"],
    verify_exp=True,
    verify_aud=True,
)


async def setup_auth(app: HealthChainAPI) -> OIDCProvider:
    """
    Setup OAuth2 authentication with Keycloak.

    Args:
        app: HealthChain API instance

    Returns:
        Initialized OIDC provider
    """
    # Initialize OIDC provider
    oidc_provider = OIDCProvider(KEYCLOAK_CONFIG)
    await oidc_provider.initialize()

    # Add JWT authentication middleware
    app.add_middleware(
        JWTAuthMiddleware,
        oidc_provider=oidc_provider,
        exclude_paths=[
            "/",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/health",
        ],
        optional_auth_paths=[
            "/api/public/*",
        ],
    )

    return oidc_provider


# Create HealthChain API
app = HealthChainAPI(
    title="HealthChain API with Keycloak Auth",
    description="Secure healthcare data API with Keycloak authentication",
    version="1.0.0",
)


# Public endpoint - no authentication required
@app.get("/")
async def root():
    """Public endpoint."""
    return {
        "message": "HealthChain API with Keycloak Authentication",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint - no authentication required."""
    return {"status": "healthy"}


# Protected endpoint - requires authentication
@app.get("/api/user/profile")
async def get_user_profile(user: dict = Depends(get_current_user)):
    """
    Get current user profile.

    Requires: Valid JWT token
    """
    if not user:
        return {"message": "Not authenticated"}

    return {
        "user_id": user.get("sub"),
        "username": user.get("preferred_username"),
        "email": user.get("email"),
        "roles": user.get("realm_access", {}).get("roles", []),
    }


# Role-based endpoints
@app.get("/api/patients")
async def list_patients(user: dict = Depends(require_role("healthcare_provider"))):
    """
    List patients - requires 'healthcare_provider' role.

    Requires: JWT token with 'healthcare_provider' role
    """
    return {
        "message": "Patient list",
        "user": user.get("preferred_username"),
        "patients": [
            {"id": 1, "name": "John Doe"},
            {"id": 2, "name": "Jane Smith"},
        ],
    }


@app.get("/api/patients/{patient_id}")
async def get_patient(
    patient_id: int,
    user: dict = Depends(require_roles(["doctor", "nurse"])),
):
    """
    Get patient details - requires 'doctor' OR 'nurse' role.

    Requires: JWT token with either 'doctor' or 'nurse' role
    """
    return {
        "message": f"Patient {patient_id} details",
        "user": user.get("preferred_username"),
        "patient": {
            "id": patient_id,
            "name": "John Doe",
            "dob": "1980-01-01",
        },
    }


@app.post("/api/prescriptions")
async def create_prescription(
    user: dict = Depends(require_role("doctor")),
):
    """
    Create prescription - requires 'doctor' role.

    Requires: JWT token with 'doctor' role
    """
    return {
        "message": "Prescription created",
        "doctor": user.get("preferred_username"),
        "prescription_id": "RX123",
    }


@app.get("/api/admin/users")
async def list_users(user: dict = Depends(require_role("admin"))):
    """
    List all users - requires 'admin' role.

    Requires: JWT token with 'admin' role
    """
    return {
        "message": "User list",
        "admin": user.get("preferred_username"),
        "users": [
            {"id": 1, "username": "doctor1", "role": "doctor"},
            {"id": 2, "username": "nurse1", "role": "nurse"},
        ],
    }


@app.get("/api/admin/audit")
async def get_audit_logs(
    user: dict = Depends(require_roles(["admin", "auditor"], require_all=False)),
):
    """
    Get audit logs - requires 'admin' OR 'auditor' role.

    Requires: JWT token with either 'admin' or 'auditor' role
    """
    return {
        "message": "Audit logs",
        "user": user.get("preferred_username"),
        "logs": [
            {"action": "login", "user": "doctor1", "timestamp": "2025-12-12T10:00:00Z"},
            {
                "action": "access_patient",
                "user": "nurse1",
                "timestamp": "2025-12-12T10:05:00Z",
            },
        ],
    }


# Scope-based endpoint (FHIR-style)
@app.get("/fhir/Patient")
async def fhir_search_patients(user: dict = Depends(require_scope("patient/*.read"))):
    """
    Search FHIR patients - requires 'patient/*.read' scope.

    Requires: JWT token with 'patient/*.read' scope
    """
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "1",
                    "name": [{"family": "Doe", "given": ["John"]}],
                }
            }
        ],
    }


# Startup event to initialize authentication
@app.on_event("startup")
async def startup_event():
    """Initialize authentication on startup."""
    try:
        oidc_provider = await setup_auth(app)
        print("✅ Keycloak authentication initialized successfully")
        print(f"   Issuer: {oidc_provider.get_issuer()}")
        print(f"   JWKS URI: {oidc_provider.config.jwks_uri}")
    except Exception as e:
        print(f"❌ Failed to initialize authentication: {e}")
        print("   The API will start but authentication will not work.")


if __name__ == "__main__":
    print("=" * 60)
    print("HealthChain API with Keycloak Authentication")
    print("=" * 60)
    print("\nStarting server...")
    print("\nTo test the API:")
    print("1. Get a token from Keycloak:")
    print(
        "   curl -X POST http://localhost:8080/realms/healthchain/protocol/openid-connect/token \\"
    )
    print("        -d 'client_id=healthchain-api' \\")
    print("        -d 'client_secret=your-secret' \\")
    print("        -d 'grant_type=password' \\")
    print("        -d 'username=your-username' \\")
    print("        -d 'password=your-password'")
    print("\n2. Use the token to access protected endpoints:")
    print("   curl http://localhost:8000/api/user/profile \\")
    print("        -H 'Authorization: Bearer <your-token>'")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
