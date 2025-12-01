#!/usr/bin/env python3
"""
Sepsis Batch Screening with FHIR Gateway

Batch process patients and write RiskAssessment resources to FHIR server.
Demonstrates querying FHIR server and writing results back.

Requirements:
- pip install healthchain joblib xgboost python-dotenv

Environment Variables:
- MEDPLUM_CLIENT_ID, MEDPLUM_CLIENT_SECRET, MEDPLUM_BASE_URL

Run:
- python sepsis_fhir_batch.py
"""

from pathlib import Path

import joblib
from dotenv import load_dotenv

from healthchain.gateway import HealthChainAPI, FHIRGateway
from healthchain.gateway.clients.fhir.base import FHIRAuthConfig
from healthchain.io import Dataset
from healthchain.pipeline import Pipeline

load_dotenv()

# Configuration
SCRIPT_DIR = Path(__file__).parent
MODEL_PATH = SCRIPT_DIR / "models" / "sepsis_model.pkl"
SCHEMA_PATH = "healthchain/configs/features/sepsis_vitals.yaml"

# Load model
model_data = joblib.load(MODEL_PATH)
model = model_data["model"]
feature_names = model_data["metadata"]["feature_names"]
threshold = model_data["metadata"]["metrics"].get("optimal_threshold", 0.5)

# FHIR Gateway
config = FHIRAuthConfig.from_env("MEDPLUM")
gateway = FHIRGateway()
gateway.add_source("fhir", config.to_connection_string())


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


def run_batch_screening():
    """
    Run batch sepsis screening.

    In production: query FHIR server for ICU patients
    For demo: load from MIMIC-on-FHIR
    """
    from healthchain.sandbox.loaders import MimicOnFHIRLoader

    pipeline = create_pipeline()

    # Load data (production would use: gateway.search(Patient, {"location": "ICU"}))
    loader = MimicOnFHIRLoader()
    bundle = loader.load(
        data_dir="../datasets/mimic-iv-clinical-database-demo-on-fhir-2.1.0/",
        resource_types=[
            "MimicObservationChartevents",
            "MimicObservationLabevents",
            "MimicPatient",
        ],
        as_dict=True,
    )

    # FHIR → Dataset → Predictions → RiskAssessments
    dataset = Dataset.from_fhir_bundle(bundle, schema=SCHEMA_PATH)
    result = pipeline(dataset)

    risk_assessments = result.to_risk_assessment(
        result.metadata["predictions"],
        result.metadata["probabilities"],
        outcome_code="A41.9",
        outcome_display="Sepsis",
        model_name="XGBoost",
    )

    print(f"Processed {len(result)} patients")
    high_risk = sum(
        1
        for ra in risk_assessments
        if ra.prediction[0].qualitativeRisk.coding[0].code == "high"
    )
    print(f"High risk: {high_risk}")

    # Write to FHIR server
    for ra in risk_assessments:
        gateway.create(ra, source="fhir")
        print(f"Created RiskAssessment/{ra.id}")

    return risk_assessments


def create_app():
    """Expose batch endpoint via API."""
    app = HealthChainAPI(title="Sepsis Batch Screening")
    app.register_gateway(gateway, path="/fhir")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    # Run batch screening
    print("=== Batch Sepsis Screening ===")
    run_batch_screening()

    # Start API server
    print("\n=== FHIR Gateway Server ===")
    print("http://localhost:8000/fhir/")
    uvicorn.run(app, port=8000)
