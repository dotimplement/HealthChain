#!/usr/bin/env python3
"""
JWKS Server for Epic FHIR Authentication

Serves your public key as a JWKS endpoint for Epic's OAuth2 JWT verification.
Use with ngrok to expose publicly for Epic App Orchard registration.

Setup:
    1. Ensure EPIC_CLIENT_SECRET_PATH in .env points to your private key PEM
    2. Set EPIC_KEY_ID in .env (e.g., "healthchain-demo-key")
    3. Run: python scripts/serve_jwks.py
    4. In another terminal: ngrok http 9999 --domain=your-static-domain.ngrok-free.app
    5. Register: https://your-static-domain.ngrok-free.app/.well-known/jwks.json in Epic

Run:
    python scripts/serve_jwks.py
"""

import os
import base64
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

load_dotenv()

app = FastAPI(title="JWKS Server for Epic FHIR")


def pem_to_jwk(pem_path: str, kid: str, alg: str = "RS384") -> dict:
    """
    Convert a PEM private key to JWK (JSON Web Key) format for JWKS.

    Args:
        pem_path: Path to PEM private key file
        kid: Key ID to identify this key in JWKS
        alg: Algorithm (default: RS384, Epic supports RS256/RS384/RS512)

    Returns:
        JWK dictionary with public key components
    """
    # Load private key
    with open(pem_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

    # Extract public key
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    # Base64url encode (no padding)
    def b64url_encode(num: int, length: int) -> str:
        """Encode integer as base64url without padding."""
        bytes_val = num.to_bytes(length, byteorder="big")
        return base64.urlsafe_b64encode(bytes_val).rstrip(b"=").decode("utf-8")

    # Calculate byte lengths for n and e
    n_length = (public_numbers.n.bit_length() + 7) // 8
    e_length = (public_numbers.e.bit_length() + 7) // 8

    return {
        "kty": "RSA",
        "use": "sig",  # Signature use
        "alg": alg,
        "kid": kid,
        "n": b64url_encode(public_numbers.n, n_length),
        "e": b64url_encode(public_numbers.e, e_length),
    }


# Load configuration at startup
PRIVATE_KEY_PATH = os.getenv("EPIC_CLIENT_SECRET_PATH")
KEY_ID = os.getenv("EPIC_KEY_ID", "healthchain-demo-key")

if not PRIVATE_KEY_PATH:
    print("❌ ERROR: EPIC_CLIENT_SECRET_PATH not set in .env")
    print("   Please set it to the path of your private key PEM file")
    exit(1)

if not Path(PRIVATE_KEY_PATH).exists():
    print(f"❌ ERROR: Private key not found at {PRIVATE_KEY_PATH}")
    exit(1)

# Generate JWKS at startup
try:
    jwk = pem_to_jwk(PRIVATE_KEY_PATH, KEY_ID)
    JWKS = {"keys": [jwk]}
    print("✓ JWKS generated successfully")
    print(f"✓ Key ID: {KEY_ID}")
    print("✓ Algorithm: RS384")
except Exception as e:
    print(f"❌ ERROR generating JWKS: {e}")
    exit(1)


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "JWKS server running",
        "endpoints": {"jwks": "/.well-known/jwks.json", "health": "/health"},
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "kid": KEY_ID}


@app.get("/.well-known/jwks.json")
def jwks_endpoint():
    """
    JWKS endpoint for Epic OAuth2 JWT verification.

    Register this URL in Epic App Orchard:
    https://your-domain/.well-known/jwks.json
    """
    return JSONResponse(content=JWKS)


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("JWKS Server for Epic FHIR Authentication")
    print("=" * 60)
    print("\n✓ Serving JWKS at: http://localhost:9999/.well-known/jwks.json")
    print(f"✓ Key ID (kid): {KEY_ID}")
    print("\nNext steps:")
    print("  1. In another terminal, run:")
    print("     ngrok http 9999 --domain=your-static-domain.ngrok-free.app")
    print("  2. Register the public URL in Epic App Orchard:")
    print("     https://your-static-domain.ngrok-free.app/.well-known/jwks.json")
    print("  3. Wait 15-30 minutes for Epic to propagate the change")
    print("  4. Test with: python scripts/check_epic_connection.py")
    print("\n" + "=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=9999, log_level="info")
