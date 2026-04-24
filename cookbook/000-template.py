#!/usr/bin/env python3
"""
[Short title — one line describing what this does]

[One sentence on the problem this solves and who it's for.]

Requirements:
    pip install healthchain [any-other-deps]

Setup:
    1. Seed test data:  healthchain seed medplum ./cookbook/data/[your-data]/
    2. Add credentials to .env:
       MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
       MEDPLUM_CLIENT_ID=your_client_id
       MEDPLUM_CLIENT_SECRET=your_client_secret
       MEDPLUM_TOKEN_URL=https://api.medplum.com/oauth2/token

Run:
    python cookbook/[your_cookbook].py
"""

from dotenv import load_dotenv
from healthchain.gateway import FHIRGateway, HealthChainAPI
from healthchain.gateway.clients import FHIRAuthConfig
from healthchain.fhir.r4b import Patient  # replace with the resources you need

load_dotenv()

# --- Setup ---

gateway = FHIRGateway()
gateway.add_source("medplum", FHIRAuthConfig.from_env("MEDPLUM").to_connection_string())

app = HealthChainAPI(title="[Your App Title]", service_type="fhir-gateway")
app.register_gateway(gateway, path="/fhir")


# --- Core logic ---

def run(patient_id: str) -> None:
    # 1. Pull FHIR resources
    bundle = gateway.search(Patient, {"_id": patient_id}, "medplum")

    # 2. Process (your model or logic here)
    result = bundle  # replace with your processing

    # 3. Return result as FHIR (e.g. Observation, RiskAssessment, etc.)
    print(result)


# --- Run ---

if __name__ == "__main__":
    # Update with IDs from: healthchain seed medplum ./cookbook/data/[your-data]/
    DEMO_PATIENT_IDS = [
        "replace-with-seeded-id",
    ]

    for patient_id in DEMO_PATIENT_IDS:
        run(patient_id)
