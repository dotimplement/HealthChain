#!/usr/bin/env python3
"""
Sepsis Risk Prediction via CDS Hooks

Real-time sepsis alerts triggered when clinician opens a patient chart.
Uses pre-extracted MIMIC patient data for demos.

Demo patients extracted from MIMIC-on-FHIR using:
    python scripts/extract_mimic_demo_patients.py

Requirements:
    pip install healthchain joblib xgboost

Run:
    python cookbook/sepsis_cds_hooks.py
"""

from pathlib import Path

import joblib
from dotenv import load_dotenv

from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.fhir import prefetch_to_bundle
from healthchain.io import Dataset
from healthchain.models import CDSRequest, CDSResponse
from healthchain.models.responses.cdsresponse import Card
from healthchain.pipeline import Pipeline

load_dotenv()

# Configuration
SCRIPT_DIR = Path(__file__).parent
MODEL_PATH = SCRIPT_DIR / "models" / "sepsis_model.pkl"
SCHEMA_PATH = (
    SCRIPT_DIR / ".." / "healthchain" / "configs" / "features" / "sepsis_vitals.yaml"
)
DEMO_PATIENTS_DIR = SCRIPT_DIR / "data" / "mimic_demo_patients"

# Load model
model_data = joblib.load(MODEL_PATH)
model = model_data["model"]
feature_names = model_data["metadata"]["feature_names"]
threshold = model_data["metadata"]["metrics"].get("optimal_threshold", 0.5)


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
        dataset.metadata["probabilities"] = probabilities
        return dataset

    return pipeline


def create_app():
    pipeline = create_pipeline()
    cds = CDSHooksService()

    @cds.hook("patient-view", id="sepsis-risk")
    def sepsis_alert(request: CDSRequest) -> CDSResponse:
        prefetch = request.prefetch or {}
        if not prefetch:
            return CDSResponse(cards=[])

        # Flatten keyed prefetch into single bundle
        bundle = prefetch_to_bundle(prefetch)

        # FHIR → Dataset → Prediction
        dataset = Dataset.from_fhir_bundle(bundle, schema=SCHEMA_PATH)
        result = pipeline(dataset)

        # print("Result:")
        # print(result.data.head(10))

        probability = float(result.metadata["probabilities"][0])
        risk = (
            "high" if probability > 0.7 else "moderate" if probability > 0.4 else "low"
        )

        if risk in ["high", "moderate"]:
            summary = f"Sepsis Risk: {risk.upper()} ({probability:.0%})"
            indicator = "critical" if risk == "high" else "warning"
            detail = (
                "**AI Guidance:**\n"
                f"- Predicted risk: **{risk.upper()}** ({probability:.0%})\n"
                "- Recommend sepsis workup and early intervention."
            )
            title = "Sepsis Alert (AI Prediction)"
            source = {
                "label": "HealthChain Sepsis Predictor",
                "url": "https://www.sccm.org/SurvivingSepsisCampaign/Guidelines/Adult-Patients",
            }
            return CDSResponse(
                cards=[
                    Card(
                        summary=summary,
                        indicator=indicator,
                        detail=detail,
                        source=source,
                        title=title,
                    )
                ]
            )

        return CDSResponse(cards=[])

    app = HealthChainAPI(title="Sepsis CDS Hooks")
    app.register_service(cds, path="/cds")

    return app


app = create_app()


if __name__ == "__main__":
    import threading
    import uvicorn
    from time import sleep
    from healthchain.sandbox import SandboxClient

    # Start server
    def run_server():
        uvicorn.run(app, port=8000, log_level="warning")

    server = threading.Thread(target=run_server, daemon=True)
    server.start()
    sleep(2)

    # Test with pre-extracted demo patients (fast, realistic per-patient data)
    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/sepsis-risk",
        workflow="patient-view",
    )
    client.load_from_path(DEMO_PATIENTS_DIR, pattern="*_patient.json")
    responses = client.send_requests()
    client.save_results(save_request=True, save_response=True, directory="./output/")

    print(f"\nProcessed {len(responses)} requests")
    for i, resp in enumerate(responses):
        cards = resp.get("cards", [])
        if cards:
            print(f"  Patient {i+1}: {cards[0].get('summary', 'No alert')}")
        else:
            print(f"  Patient {i+1}: Low risk (no alert)")

    server.join()
