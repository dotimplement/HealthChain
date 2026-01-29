#!/usr/bin/env python3
"""
Generate RSA private key and X.509 certificate for Epic FHIR authentication.

This script does the equivalent of:
    openssl genrsa -out privatekey.pem 2048
    openssl req -new -x509 -key privatekey.pem -out publickey509.pem -subj '/CN=PrioAuthApp'

Usage:
    python generate_private_key.py
"""

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.x509.oid import NameOID
import datetime

# Generate a 2048-bit RSA private key
print("Generating 2048-bit RSA private key...")
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# Serialize private key to PEM format
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Save private key to file
private_file = "privatekey.pem"
with open(private_file, "wb") as f:
    f.write(private_pem)

print(f"✓ Private key generated: {private_file}")

# Generate X.509 certificate (self-signed)
print("Generating X.509 certificate...")
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, u"PrioAuthApp"),
])

cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    private_key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.utcnow()
).not_valid_after(
    datetime.datetime.utcnow() + datetime.timedelta(days=365)
).sign(private_key, hashes.SHA256(), default_backend())

# Serialize certificate to PEM format
cert_pem = cert.public_bytes(serialization.Encoding.PEM)

# Save certificate to file
cert_file = "publickey509.pem"
with open(cert_file, "wb") as f:
    f.write(cert_pem)

print(f"✓ X.509 certificate generated: {cert_file}")
print(f"✓ Certificate CN: PriorAuthApp")
print(f"✓ Certificate valid for: 365 days")

print("\n" + "=" * 50)
print("SUCCESS - Files Generated:")
print("=" * 50)
print(f"1. {private_file}")
print(f"   → Use this in EPIC_CLIENT_SECRET_PATH")
print(f"\n2. {cert_file}")
print(f"   → Upload this to Epic App Orchard")
print("\n" + "=" * 50)
