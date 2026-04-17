#!/usr/bin/env python3
"""
Seed Medplum with a synthetic cancer patient for the ATCC and FHIR Q&A demos.

Setup:
    1. Sign up at https://app.medplum.com and create a client application
       (Settings → Security → Client Applications → New Client)
    2. Add to .env:
           MEDPLUM_CLIENT_ID=your_client_id
           MEDPLUM_CLIENT_SECRET=your_client_secret
           MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
           MEDPLUM_TOKEN_URL=https://api.medplum.com/oauth2/token

Run:
    uv run python cookbook/data/medplum_seed.py

Output:
    Prints the created patient ID — add it to .env as DEMO_PATIENT_ID.
"""

import httpx
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse

from healthchain.gateway.clients.fhir.base import FHIRAuthConfig
from healthchain.gateway.clients.auth import OAuth2TokenManager

load_dotenv()

config = FHIRAuthConfig.from_env("MEDPLUM")
_token_manager = OAuth2TokenManager(config.to_oauth2_config())


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {_token_manager.get_access_token()}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }


def _transaction_url(raw_base_url: str) -> str:
    """Normalize base URL so httpx always receives an HTTP(S) endpoint."""
    parsed = urlparse(raw_base_url)

    if parsed.scheme == "fhir":
        # Support connection-string style env values:
        # fhir://host/path?client_id=...&token_url=...
        return urlunparse(("https", parsed.netloc, parsed.path, "", "", "")).rstrip("/")

    if parsed.scheme in {"http", "https"}:
        # Drop query params if someone copied a connection-string-like URL into BASE_URL.
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
        ).rstrip("/")

    raise ValueError(
        f"Unsupported MEDPLUM_BASE_URL scheme '{parsed.scheme or '<missing>'}'. "
        "Use https://... or fhir://..."
    )


PATIENT = {
    "resourceType": "Patient",
    "name": [{"use": "official", "given": ["Sarah"], "family": "Johnson"}],
    "gender": "female",
    "birthDate": "1979-03-15",
}


def _resources(patient_id: str) -> list:
    ref = f"Patient/{patient_id}"
    return [
        {
            "resourceType": "Condition",
            "subject": {"reference": ref},
            "code": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/icd-10",
                        "code": "C53.9",
                        "display": "Malignant neoplasm of cervix uteri, unspecified",
                    }
                ],
                "text": "Cervical cancer",
            },
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                    }
                ]
            },
            "onsetDateTime": "2025-11-01",
        },
        {
            "resourceType": "Appointment",
            "status": "booked",
            "description": "Colposcopy follow-up",
            "start": "2026-04-10T10:00:00Z",
            "end": "2026-04-10T10:30:00Z",
            "participant": [
                {
                    "actor": {"reference": ref},
                    "status": "accepted",
                }
            ],
        },
        {
            "resourceType": "CarePlan",
            "status": "active",
            "intent": "plan",
            "subject": {"reference": ref},
            "title": "Cervical Cancer Treatment Plan",
            "description": (
                "Stage IB cervical cancer. Treatment: radical hysterectomy followed by "
                "adjuvant chemoradiation if margins involved. Monthly monitoring for 2 years. "
                "Clinical nurse specialist available Mon-Fri 09:00-17:00, ext. 4821."
            ),
        },
    ]


def main():
    base_url = _transaction_url(config.base_url)
    with httpx.Client(timeout=30) as client:
        # Step 1: create patient, get real ID
        r = client.post(f"{base_url}/Patient", headers=_auth_headers(), json=PATIENT)
        r.raise_for_status()
        patient_id = r.json()["id"]

        # Step 2: create remaining resources referencing the real patient ID
        for resource in _resources(patient_id):
            r = client.post(
                f"{base_url}/{resource['resourceType']}",
                headers=_auth_headers(),
                json=resource,
            )
            r.raise_for_status()

    print("Seeded patient: Sarah Johnson (cervical cancer, stage IB)")
    print(f"Patient ID: {patient_id}")
    print(f"\nAdd to .env:\n    DEMO_PATIENT_ID={patient_id}")


if __name__ == "__main__":
    main()
