#!/usr/bin/env python3
"""
Extract Demo Patient Prefetch from MIMIC-on-FHIR

Creates CDS Hooks prefetch files with only the observations needed for
sepsis prediction, keyed by feature name. Much smaller than full bundles!

Customize:
    - MIMIC_DIR: Path to your MIMIC-on-FHIR dataset
    - MODEL_PATH: Path to your trained model pickle
    - SCHEMA_PATH: Feature schema defining which observations to extract
    - OUTPUT_DIR: Where to save extracted patient files
    - NUM_PATIENTS_PER_RISK: How many patients to extract per risk level

Run:
    python scripts/extract_mimic_demo_patients.py

Output format:
    {
      "patient": {...Patient resource...},
      "heart_rate": {"resourceType": "Bundle", "entry": [...]},
      "temperature": {"resourceType": "Bundle", "entry": [...]},
      ...
    }
"""

import json
from pathlib import Path

import joblib
import yaml

from healthchain.sandbox.loaders import MimicOnFHIRLoader
from healthchain.io import Dataset
from healthchain.pipeline import Pipeline

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print(
        "Warning: dotenv not installed. Please manually set the MIMIC_FHIR_PATH environment variable."
    )


# =============================================================================
# CUSTOMIZE THESE
# =============================================================================

MIMIC_DIR = os.getenv("MIMIC_FHIR_PATH")
MODEL_PATH = "cookbook/models/sepsis_model.pkl"
SCHEMA_PATH = "healthchain/configs/features/sepsis_vitals.yaml"
OUTPUT_DIR = Path("cookbook/data/mimic_demo_patients")

# Number of patients to extract per risk level (high/moderate/low)
NUM_PATIENTS_PER_RISK = 1

# =============================================================================


def load_observation_codes(schema_path: str) -> dict:
    """Load feature schema and extract observation codes."""
    with open(schema_path) as f:
        schema = yaml.safe_load(f)

    codes = {}
    for feature_name, config in schema["features"].items():
        if config.get("fhir_resource") == "Observation":
            codes[config["code"]] = feature_name
    return codes


def create_pipeline(model, feature_names) -> Pipeline[Dataset]:
    """Build prediction pipeline."""
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


def get_observation_code(resource: dict) -> str:
    """Extract MIMIC code from Observation resource."""
    for coding in resource.get("code", {}).get("coding", []):
        if "mimic" in coding.get("system", ""):
            return coding.get("code", "")
    return ""


def extract_patient_prefetch(bundle: dict, patient_ref: str, obs_codes: dict) -> dict:
    """Extract keyed prefetch for a patient with only needed observations."""
    patient_id = patient_ref.split("/")[-1]
    prefetch = {}
    feature_obs = {name: [] for name in obs_codes.values()}

    for entry in bundle["entry"]:
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType", "")

        if resource_type == "Patient" and resource.get("id") == patient_id:
            prefetch["patient"] = resource

        elif resource_type == "Observation":
            subject = resource.get("subject", {})
            if subject.get("reference", "").endswith(patient_id):
                code = get_observation_code(resource)
                if code in obs_codes:
                    feature_obs[obs_codes[code]].append(entry)

    for feature_name, entries in feature_obs.items():
        if entries:
            prefetch[feature_name] = {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": entries,
            }

    return prefetch


def main():
    print("=" * 60)
    print("MIMIC Demo Patient Extraction")
    print("=" * 60)

    if MIMIC_DIR is None:
        print("Error: MIMIC_FHIR_PATH environment variable is not set.")
        return

    # Load configs
    obs_codes = load_observation_codes(SCHEMA_PATH)
    print(f"Features to extract: {list(obs_codes.values())}")

    model_data = joblib.load(MODEL_PATH)
    model = model_data["model"]
    feature_names = model_data["metadata"]["feature_names"]
    print(f"Model features: {feature_names}")

    # Load MIMIC data
    print("\nLoading MIMIC-on-FHIR...")
    loader = MimicOnFHIRLoader()
    bundle = loader.load(
        data_dir=MIMIC_DIR,
        resource_types=[
            "MimicObservationChartevents",
            "MimicObservationLabevents",
            "MimicPatient",
        ],
        as_dict=True,
    )
    print(f"Loaded {len(bundle['entry']):,} resources")

    # Run predictions
    print("\nExtracting features and predicting...")
    dataset = Dataset.from_fhir_bundle(bundle, schema=SCHEMA_PATH)
    pipeline = create_pipeline(model, feature_names)
    result = pipeline(dataset)

    df = result.data.copy()
    df["probability"] = result.metadata["probabilities"]
    df["risk"] = df["probability"].apply(
        lambda p: "high" if p > 0.7 else "moderate" if p > 0.4 else "low"
    )

    print(f"\nRisk distribution ({len(df)} patients):")
    print(df["risk"].value_counts().to_string())

    # Select patients per risk level
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    patients_to_extract = []

    for risk_level in ["high", "moderate", "low"]:
        risk_patients = df[df["risk"] == risk_level]
        for i in range(min(NUM_PATIENTS_PER_RISK, len(risk_patients))):
            patient = risk_patients.iloc[i]
            label = (
                f"{risk_level}_risk"
                if NUM_PATIENTS_PER_RISK == 1
                else f"{risk_level}_risk_{i+1}"
            )
            patients_to_extract.append((label, patient))

    # Extract and save
    print(f"\nExtracting to {OUTPUT_DIR}/")
    for label, patient in patients_to_extract:
        prefetch = extract_patient_prefetch(bundle, patient["patient_ref"], obs_codes)

        output_file = OUTPUT_DIR / f"{label}_patient.json"
        with open(output_file, "w") as f:
            json.dump(prefetch, f, indent=2, default=str)

        obs_count = sum(
            len(v.get("entry", [])) for k, v in prefetch.items() if k != "patient"
        )
        features_with_data = [k for k in prefetch if k != "patient"]
        print(
            f"  {label}: {patient['probability']:.1%} risk, {obs_count} obs ({', '.join(features_with_data)})"
        )

    print("\nDone! Use these files with SandboxClient.load_from_path()")


if __name__ == "__main__":
    main()
