#!/usr/bin/env python3
"""
Sepsis Batch Screening with FHIR Gateway

Query patients from a FHIR server, batch run sepsis predictions, and write
RiskAssessment resources back. Demonstrates real FHIR server integration.

Setup:
    1. Extract and upload demo patients:
       python scripts/extract_mimic_demo_patients.py --minimal --upload
    2. Update DEMO_PATIENT_IDS below with the server-assigned IDs
    3. Set env vars: MEDPLUM_CLIENT_ID, MEDPLUM_CLIENT_SECRET, MEDPLUM_BASE_URL

Run:
    python cookbook/sepsis_fhir_batch.py
"""

from pathlib import Path
from typing import List

import joblib
import logging
from dotenv import load_dotenv
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.riskassessment import RiskAssessment

from healthchain.gateway import HealthChainAPI, FHIRGateway
from healthchain.gateway.clients.fhir.base import FHIRAuthConfig
from healthchain.fhir import merge_bundles
from healthchain.io import Dataset
from healthchain.pipeline import Pipeline

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
SCRIPT_DIR = Path(__file__).parent
MODEL_PATH = SCRIPT_DIR / "models" / "sepsis_model.pkl"
SCHEMA_PATH = (
    SCRIPT_DIR / ".." / "healthchain" / "configs" / "features" / "sepsis_vitals.yaml"
)

# Load model
model_data = joblib.load(MODEL_PATH)
model = model_data["model"]
feature_names = model_data["metadata"]["feature_names"]
threshold = model_data["metadata"]["metrics"].get("optimal_threshold", 0.5)

# FHIR sources (configure via environment)
MEDPLUM_URL = None
EPIC_URL = None

try:
    config = FHIRAuthConfig.from_env("MEDPLUM")
    MEDPLUM_URL = config.to_connection_string()
except Exception:
    logger.warning("Failed to load Medplum config")

try:
    config = FHIRAuthConfig.from_env("EPIC")
    EPIC_URL = config.to_connection_string()
except Exception:
    logger.warning("Failed to load Epic config")


def get_risk_summary(ra: RiskAssessment) -> tuple[str, float]:
    """Extract risk level and probability from a RiskAssessment."""
    pred = ra.prediction[0]
    return pred.qualitativeRisk.coding[0].code, pred.probabilityDecimal


def create_pipeline() -> Pipeline[Dataset]:
    """Build sepsis prediction pipeline."""
    pipeline = Pipeline[Dataset]()

    @pipeline.add_node
    def impute_missing(dataset: Dataset) -> Dataset:
        dataset.data = dataset.data.fillna(dataset.data.median(numeric_only=True))
        return dataset

    @pipeline.add_node
    def run_inference(dataset: Dataset) -> Dataset:
        features = dataset.data[feature_names]
        probabilities = model.predict_proba(features)[:, 1]
        predictions = (probabilities >= threshold).astype(int)
        dataset.metadata["predictions"] = predictions
        dataset.metadata["probabilities"] = probabilities
        return dataset

    return pipeline


def screen_patient(
    gateway: FHIRGateway, pipeline: Pipeline, patient_id: str, source: str
) -> RiskAssessment | None:
    """Screen a single patient for sepsis risk. Returns RiskAssessment or None."""
    # Query patient data from FHIR server
    obs_bundle = gateway.search(
        Observation, {"patient": patient_id, "_count": "100"}, source
    )
    patient_bundle = gateway.search(Patient, {"_id": patient_id}, source)

    # Merge into single bundle
    bundle = merge_bundles([patient_bundle, obs_bundle])

    if not bundle.entry:
        return None

    # FHIR → Dataset → Prediction
    dataset = Dataset.from_fhir_bundle(bundle, schema=str(SCHEMA_PATH))

    if len(dataset.data) == 0:
        return None

    result = pipeline(dataset)

    # Create and save RiskAssessment
    risk_assessments = result.to_risk_assessment(
        outcome_code="A41.9",
        outcome_display="Sepsis",
        model_name="sepsis_xgboost_v1",
    )

    for ra in risk_assessments:
        gateway.create(ra, source=source)

    return risk_assessments[0] if risk_assessments else None


def batch_screen(
    gateway: FHIRGateway, patient_ids: List[str], source: str = "medplum"
) -> None:
    """Screen multiple patients for sepsis risk."""
    pipeline = create_pipeline()

    for patient_id in patient_ids:
        try:
            ra = screen_patient(gateway, pipeline, patient_id, source)
            if ra:
                risk, prob = get_risk_summary(ra)
                print(
                    f"  {patient_id}: {risk.upper()} ({prob:.0%}) → RiskAssessment/{ra.id}"
                )
            else:
                print(f"  {patient_id}: No data")
        except Exception as e:
            print(f"  {patient_id}: Error - {e}")


def create_app():
    """Create FHIR gateway app with configured sources."""
    gateway = FHIRGateway()

    # Add configured sources
    if MEDPLUM_URL:
        gateway.add_source("medplum", MEDPLUM_URL)
        logger.info("✓ Medplum configured")
    if EPIC_URL:
        gateway.add_source("epic", EPIC_URL)
        logger.info("✓ Epic configured")

    app = HealthChainAPI(title="Sepsis Batch Screening")
    app.register_gateway(gateway, path="/fhir")

    return app, gateway


app, gateway = create_app()


if __name__ == "__main__":
    # Demo patient IDs from: python scripts/extract_mimic_demo_patients.py --minimal --upload
    # (Update these with server-assigned IDs after upload)
    DEMO_PATIENT_IDS = [
        "702e11e8-6d21-41dd-9b48-31715fdc0fb1",  # high risk
        "3b0da7e9-0379-455a-8d35-bedd3a6ee459",  # moderate risk
        "f490ceb4-6262-4f1e-8b72-5515e6c46741",  # low risk
    ]

    # Screen Medplum patients
    if MEDPLUM_URL:
        print("\n=== Screening patients from Medplum ===")
        batch_screen(gateway, DEMO_PATIENT_IDS, source="medplum")

    # Demo Epic connectivity (data may not match sepsis features)
    if EPIC_URL:
        print("\n=== Epic Sandbox (demo connectivity) ===")
        batch_screen(gateway, ["e0w0LEDCYtfckT6N.CkJKCw3"], source="epic")
