#!/usr/bin/env python3
"""
Extract Demo Patients from MIMIC-on-FHIR

Extracts patient data for sepsis prediction demos. Creates small files with
only the observations needed for the model.

Usage:
    # For CDS Hooks demo (prefetch format)
    python scripts/extract_mimic_demo_patients.py --minimal

    # For FHIR batch demo (upload to Medplum)
    python scripts/extract_mimic_demo_patients.py --minimal --upload

Output formats:
  Default (prefetch for CDS Hooks):
    {"patient": {...}, "heart_rate": {"entry": [...]}, ...}

  --bundle (for FHIR server upload):
    {"resourceType": "Bundle", "type": "transaction", "entry": [...]}

Requires:
    - MIMIC_FHIR_PATH env var (or --mimic flag)
    - MEDPLUM_* env vars (if using --upload)
"""

import argparse
import json
import os
import uuid
from pathlib import Path

import joblib
import yaml

from healthchain.io import Dataset
from healthchain.pipeline import Pipeline
from healthchain.sandbox.loaders import MimicOnFHIRLoader

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_MODEL_PATH = "cookbook/models/sepsis_model.pkl"
DEFAULT_SCHEMA_PATH = "healthchain/configs/features/sepsis_vitals.yaml"
DEFAULT_OUTPUT_DIR = Path("cookbook/data/mimic_demo_patients")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_observation_codes(schema_path: str) -> dict:
    """Extract observation codes from feature schema."""
    with open(schema_path) as f:
        schema = yaml.safe_load(f)
    return {
        config["code"]: name
        for name, config in schema["features"].items()
        if config.get("fhir_resource") == "Observation"
    }


def create_pipeline(model, feature_names) -> Pipeline[Dataset]:
    """Build prediction pipeline for risk stratification."""
    pipeline = Pipeline[Dataset]()

    @pipeline.add_node
    def impute_missing(dataset: Dataset) -> Dataset:
        dataset.data = dataset.data.fillna(dataset.data.median(numeric_only=True))
        return dataset

    @pipeline.add_node
    def run_inference(dataset: Dataset) -> Dataset:
        features = dataset.data[feature_names]
        dataset.metadata["probabilities"] = model.predict_proba(features)[:, 1]
        return dataset

    return pipeline


def get_observation_code(resource: dict) -> str:
    """Extract MIMIC code from Observation."""
    for coding in resource.get("code", {}).get("coding", []):
        if "mimic" in coding.get("system", ""):
            return coding.get("code", "")
    return ""


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================


def extract_patient_prefetch(
    bundle: dict, patient_ref: str, obs_codes: dict, minimal: bool = False
) -> dict:
    """Extract keyed prefetch for a patient (CDS Hooks format)."""
    patient_id = patient_ref.split("/")[-1]
    prefetch = {}
    feature_obs = {name: [] for name in obs_codes.values()}

    for entry in bundle["entry"]:
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType", "")

        if rtype == "Patient" and resource.get("id") == patient_id:
            prefetch["patient"] = resource
        elif rtype == "Observation":
            ref = resource.get("subject", {}).get("reference", "")
            if ref.endswith(patient_id):
                code = get_observation_code(resource)
                if code in obs_codes:
                    feature_obs[obs_codes[code]].append(entry)

    for name, entries in feature_obs.items():
        if entries:
            if minimal:
                entries = entries[-1:]  # Keep only latest
            prefetch[name] = {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": entries,
            }

    return prefetch


def prefetch_to_bundle(prefetch: dict) -> dict:
    """Convert prefetch to FHIR transaction Bundle (for server upload)."""
    entries = []
    # Use urn:uuid references so Medplum properly links Observations to Patient.
    patient_uuid = f"urn:uuid:{uuid.uuid4()}"

    # Patient
    if "patient" in prefetch:
        entries.append(
            {
                "fullUrl": patient_uuid,
                "resource": prefetch["patient"].copy(),
                "request": {"method": "POST", "url": "Patient"},
            }
        )

    # Observations (with updated subject reference)
    for key, value in prefetch.items():
        if key == "patient" or not isinstance(value, dict):
            continue
        for entry in value.get("entry", []):
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Observation":
                obs = resource.copy()
                obs["subject"] = {"reference": patient_uuid}
                entries.append(
                    {
                        "fullUrl": f"urn:uuid:{uuid.uuid4()}",
                        "resource": obs,
                        "request": {"method": "POST", "url": "Observation"},
                    }
                )

    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def upload_bundle(gateway, bundle_data: dict) -> str:
    """Upload bundle to Medplum, return server-assigned Patient ID."""
    from fhir.resources.bundle import Bundle as FHIRBundle

    response = gateway.transaction(FHIRBundle(**bundle_data), source="medplum")

    # Extract Patient ID from response
    if response.entry:
        for entry in response.entry:
            if entry.response and entry.response.location:
                loc = entry.response.location
                if "Patient/" in loc:
                    return loc.split("Patient/")[1].split("/")[0]
    return None


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Extract demo patients from MIMIC-on-FHIR"
    )
    parser.add_argument("--mimic", type=str, help="Path to MIMIC-on-FHIR dataset")
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL_PATH, help="Model pickle path"
    )
    parser.add_argument(
        "--schema", type=str, default=DEFAULT_SCHEMA_PATH, help="Feature schema YAML"
    )
    parser.add_argument(
        "--minimal", action="store_true", help="Keep only 1 obs per feature (~12KB)"
    )
    parser.add_argument("--bundle", action="store_true", help="Output as FHIR Bundle")
    parser.add_argument("--upload", action="store_true", help="Upload to Medplum")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-patients-per-risk", type=int, default=1)
    args = parser.parse_args()

    mimic_dir = args.mimic or os.getenv("MIMIC_FHIR_PATH")
    if not mimic_dir:
        print("Error: Set MIMIC_FHIR_PATH or use --mimic")
        return

    # --upload implies --bundle
    if args.upload:
        args.bundle = True

    # Set up FHIRGateway for upload
    gateway = None
    if args.upload:
        from healthchain.gateway import FHIRGateway
        from healthchain.gateway.clients.fhir.base import FHIRAuthConfig

        try:
            config = FHIRAuthConfig.from_env("MEDPLUM")
            gateway = FHIRGateway()
            gateway.add_source("medplum", config.to_connection_string())
            print("✓ Medplum configured")
        except Exception as e:
            print(f"✗ Medplum failed: {e}")
            return

    print("=" * 60)
    print("MIMIC Demo Patient Extraction" + (" (MINIMAL)" if args.minimal else ""))
    print("=" * 60)

    # Load schema and model
    obs_codes = load_observation_codes(args.schema)
    print(f"Features: {list(obs_codes.values())}")

    model_data = joblib.load(args.model)
    model = model_data["model"]
    feature_names = model_data["metadata"]["feature_names"]

    # Load MIMIC data
    print("\nLoading MIMIC-on-FHIR...")
    loader = MimicOnFHIRLoader()
    bundle = loader.load(
        data_dir=mimic_dir,
        resource_types=[
            "MimicObservationChartevents",
            "MimicObservationLabevents",
            "MimicPatient",
        ],
        as_dict=True,
    )
    print(f"Loaded {len(bundle['entry']):,} resources")

    # Run predictions
    print("\nExtracting features...")
    dataset = Dataset.from_fhir_bundle(bundle, schema=args.schema)
    result = create_pipeline(model, feature_names)(dataset)

    df = result.data.copy()
    df["probability"] = result.metadata["probabilities"]
    df["risk"] = df["probability"].apply(
        lambda p: "high" if p > 0.7 else "moderate" if p > 0.4 else "low"
    )

    print(f"\nRisk distribution ({len(df)} patients):")
    print(df["risk"].value_counts().to_string())

    # Extract patients
    args.output.mkdir(parents=True, exist_ok=True)
    print(f"\nExtracting to {args.output}/")

    uploaded_ids = []  # Track server-assigned IDs for copy-paste output

    for risk_level in ["high", "moderate", "low"]:
        risk_df = df[df["risk"] == risk_level]
        if len(risk_df) == 0:
            continue

        risk_df = risk_df.sample(
            n=min(args.num_patients_per_risk, len(risk_df)), random_state=args.seed
        )

        for i, (_, patient) in enumerate(risk_df.iterrows()):
            label = (
                f"{risk_level}_risk"
                if args.num_patients_per_risk == 1
                else f"{risk_level}_risk_{i+1}"
            )
            prefetch = extract_patient_prefetch(
                bundle, patient["patient_ref"], obs_codes, args.minimal
            )

            # Output format
            if args.bundle:
                output_data = prefetch_to_bundle(prefetch)
                suffix = "_bundle.json"
            else:
                output_data = prefetch
                suffix = "_patient.json"

            # Save file
            with open(args.output / f"{label}{suffix}", "w") as f:
                json.dump(output_data, f, indent=2, default=str)

            obs_count = sum(
                len(v.get("entry", [])) for k, v in prefetch.items() if k != "patient"
            )
            patient_id = patient["patient_ref"].split("/")[-1]

            # Upload if requested
            status = ""
            if args.upload and gateway:
                server_id = upload_bundle(gateway, output_data)
                if server_id:
                    uploaded_ids.append((server_id, risk_level))
                    status = f" ✓ uploaded (ID: {server_id})"
                else:
                    status = " ✓ uploaded"

            print(
                f"  {label}: {patient_id} ({patient['probability']:.1%}, {obs_count} obs){status}"
            )

    # Print next steps
    print("\n" + "=" * 60)
    if args.upload:
        print("✓ Uploaded to Medplum!")
        if uploaded_ids:
            print("\nCopy this into sepsis_fhir_batch.py:\n")
            print("DEMO_PATIENT_IDS = [")
            for server_id, risk in uploaded_ids:
                print(f'    "{server_id}",  # {risk} risk')
            print("]")
    elif args.bundle:
        print("Re-run with --upload to upload to Medplum")
    else:
        print("CDS: client.load_from_path('cookbook/data/mimic_demo_patients/')")


if __name__ == "__main__":
    main()
