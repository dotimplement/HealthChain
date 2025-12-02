#!/usr/bin/env python3
"""
Quick Epic FHIR connection test.

Run: python scripts/check_epic_connection.py
"""

from dotenv import load_dotenv

load_dotenv()


def main():
    print("=" * 50)
    print("Epic FHIR Connection Test")
    print("=" * 50)

    # 1. Load config
    print("\n1. Loading config from environment...")
    try:
        from healthchain.gateway.clients.fhir.base import FHIRAuthConfig

        config = FHIRAuthConfig.from_env("EPIC")
        print(f"   ✓ client_id: {config.client_id[:8]}...")
        print(f"   ✓ token_url: {config.token_url}")
        print(f"   ✓ base_url: {config.base_url}")
        print(f"   ✓ use_jwt_assertion: {config.use_jwt_assertion}")
    except Exception as e:
        print(f"   ✗ Failed to load config: {e}")
        return False

    # 2. Test JWT creation
    print("\n2. Creating JWT assertion...")
    try:
        oauth_config = config.to_oauth2_config()
        from healthchain.gateway.clients.auth import OAuth2TokenManager

        manager = OAuth2TokenManager(oauth_config)
        jwt = manager._create_jwt_assertion()
        print(f"   ✓ JWT created ({len(jwt)} chars)")
    except Exception as e:
        print(f"   ✗ JWT creation failed: {e}")
        return False

    # 3. Get access token
    print("\n3. Requesting access token from Epic...")
    try:
        token = manager.get_access_token()
        print(f"   ✓ Token received: {token[:20]}...")
    except Exception as e:
        print(f"   ✗ Token request failed: {e}")
        print("\n   Possible causes:")
        print("   - App changes still propagating (wait 15-30 min)")
        print("   - Public key not registered in Epic App Orchard")
        print("   - App not in 'Ready for Sandbox' state")
        return False

    # 4. Test FHIR endpoint
    print("\n4. Testing FHIR endpoint (CapabilityStatement)...")
    try:
        from healthchain.gateway.clients.fhir.sync.client import FHIRClient

        client = FHIRClient(config)
        caps = client.capabilities()
        print(f"   ✓ FHIR server: {caps.software.name if caps.software else 'Unknown'}")
        print(f"   ✓ FHIR version: {caps.fhirVersion}")
    except Exception as e:
        print(f"   ✗ FHIR request failed: {e}")
        return False

    # 5. Test patient read (optional)
    print("\n5. Testing Patient read...")
    test_patient_id = "e0w0LEDCYtfckT6N.CkJKCw3"  # Epic sandbox patient
    try:
        from fhir.resources.patient import Patient

        patient = client.read(Patient, test_patient_id)
        name = patient.name[0] if patient.name else None
        print(
            f"   ✓ Patient: {name.given[0] if name and name.given else '?'} {name.family if name else '?'}"
        )
    except Exception as e:
        print(f"   ⚠ Patient read failed: {e}")
        print("   (This may be a permissions issue, not a connection issue)")

    print("\n" + "=" * 50)
    print("✓ Epic connection working!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
