#!/usr/bin/env python3
"""
Sepsis Prediction Training Script

Trains Random Forest, XGBoost, and Logistic Regression models for sepsis prediction
using MIMIC-IV clinical database data.

Requirements:
- pip install scikit-learn xgboost joblib pandas numpy

Run:
- python sepsis_prediction_training.py
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List, Any, Union

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
)
import xgboost as xgb
import joblib


# MIMIC-IV ItemID mappings for features
CHARTEVENTS_ITEMIDS = {
    "heart_rate": 220050,
    "temperature_f": 223761,
    "temperature_c": 223762,
    "respiratory_rate": 220210,
}

LABEVENTS_ITEMIDS = {
    "wbc": [51300, 51301],  # White Blood Cell Count
    "lactate": 50813,
    "creatinine": 50912,
}

# Sepsis ICD-10 codes
SEPSIS_ICD10_CODES = [
    "A41.9",  # Sepsis, unspecified organism
    "A40",  # Streptococcal sepsis (starts with)
    "A41",  # Other sepsis (starts with)
    "R65.20",  # Severe sepsis without shock
    "R65.21",  # Severe sepsis with shock
    "R65.1",  # SIRS (Systemic Inflammatory Response Syndrome)
    "A41.0",  # Sepsis due to Streptococcus, group A
    "A41.1",  # Sepsis due to Streptococcus, group B
    "A41.2",  # Sepsis due to other specified streptococci
    "A41.3",  # Sepsis due to Haemophilus influenzae
    "A41.4",  # Sepsis due to anaerobes
    "A41.5",  # Sepsis due to other Gram-negative organisms
    "A41.50",  # Sepsis due to unspecified Gram-negative organism
    "A41.51",  # Sepsis due to Escherichia coli
    "A41.52",  # Sepsis due to Pseudomonas
    "A41.53",  # Sepsis due to Serratia
    "A41.59",  # Sepsis due to other Gram-negative organisms
    "A41.8",  # Other specified sepsis
    "A41.81",  # Sepsis due to Enterococcus
    "A41.89",  # Other specified sepsis
]

# Sepsis ICD-9 codes (for older data)
SEPSIS_ICD9_CODES = [
    "038",  # Septicemia (starts with)
    "99591",  # Sepsis
    "99592",  # Severe sepsis
    "78552",  # Septic shock
]


def load_mimic_data(data_dir: str) -> Dict[str, pd.DataFrame]:
    """
    Load all required MIMIC-IV CSV tables.

    Args:
        data_dir: Path to MIMIC-IV dataset directory

    Returns:
        Dictionary mapping table names to DataFrames
    """
    data_dir = Path(data_dir)

    print("Loading MIMIC-IV data...")

    tables = {
        "patients": pd.read_csv(
            data_dir / "hosp" / "patients.csv.gz", compression="gzip", low_memory=False
        ),
        "admissions": pd.read_csv(
            data_dir / "hosp" / "admissions.csv.gz",
            compression="gzip",
            low_memory=False,
        ),
        "icustays": pd.read_csv(
            data_dir / "icu" / "icustays.csv.gz", compression="gzip", low_memory=False
        ),
        "chartevents": pd.read_csv(
            data_dir / "icu" / "chartevents.csv.gz",
            compression="gzip",
            low_memory=False,
        ),
        "labevents": pd.read_csv(
            data_dir / "hosp" / "labevents.csv.gz", compression="gzip", low_memory=False
        ),
        "diagnoses_icd": pd.read_csv(
            data_dir / "hosp" / "diagnoses_icd.csv.gz",
            compression="gzip",
            low_memory=False,
        ),
    }

    print(f"Loaded {len(tables)} tables")
    for name, df in tables.items():
        print(f"  {name}: {len(df)} rows")

    return tables


def extract_chartevents_features(
    chartevents: pd.DataFrame, icustays: pd.DataFrame
) -> pd.DataFrame:
    """
    Extract 2-3 vital signs from chartevents table.

    Args:
        chartevents: Chart events DataFrame
        icustays: ICU stays DataFrame

    Returns:
        DataFrame with features per stay_id
    """
    print("Extracting chartevents features...")

    # Filter to relevant itemids
    relevant_itemids = list(CHARTEVENTS_ITEMIDS.values())
    chartevents_filtered = chartevents[
        chartevents["itemid"].isin(relevant_itemids)
    ].copy()

    # Merge with icustays to get stay times
    chartevents_merged = chartevents_filtered.merge(
        icustays[["stay_id", "intime", "outtime"]], on="stay_id", how="inner"
    )

    # Convert charttime to datetime
    chartevents_merged["charttime"] = pd.to_datetime(chartevents_merged["charttime"])
    chartevents_merged["intime"] = pd.to_datetime(chartevents_merged["intime"])

    # Filter to first 24 hours of ICU stay
    chartevents_merged = chartevents_merged[
        (chartevents_merged["charttime"] >= chartevents_merged["intime"])
        & (
            chartevents_merged["charttime"]
            <= chartevents_merged["intime"] + pd.Timedelta(hours=24)
        )
    ]

    # Extract numeric values
    chartevents_merged["valuenum"] = pd.to_numeric(
        chartevents_merged["valuenum"], errors="coerce"
    )

    # Aggregate by stay_id and itemid (take mean)
    features = []

    for stay_id in icustays["stay_id"].unique():
        stay_data = chartevents_merged[chartevents_merged["stay_id"] == stay_id]

        feature_row = {"stay_id": stay_id}

        # Heart Rate
        hr_data = stay_data[stay_data["itemid"] == CHARTEVENTS_ITEMIDS["heart_rate"]][
            "valuenum"
        ]
        feature_row["heart_rate"] = hr_data.mean() if not hr_data.empty else np.nan

        # Temperature (prefer Celsius, convert Fahrenheit if needed)
        temp_c = stay_data[stay_data["itemid"] == CHARTEVENTS_ITEMIDS["temperature_c"]][
            "valuenum"
        ]
        temp_f = stay_data[stay_data["itemid"] == CHARTEVENTS_ITEMIDS["temperature_f"]][
            "valuenum"
        ]

        if not temp_c.empty:
            feature_row["temperature"] = temp_c.mean()
        elif not temp_f.empty:
            # Convert Fahrenheit to Celsius
            feature_row["temperature"] = (temp_f.mean() - 32) * 5 / 9
        else:
            feature_row["temperature"] = np.nan

        # Respiratory Rate
        rr_data = stay_data[
            stay_data["itemid"] == CHARTEVENTS_ITEMIDS["respiratory_rate"]
        ]["valuenum"]
        feature_row["respiratory_rate"] = (
            rr_data.mean() if not rr_data.empty else np.nan
        )

        features.append(feature_row)

    return pd.DataFrame(features)


def extract_labevents_features(
    labevents: pd.DataFrame, icustays: pd.DataFrame
) -> pd.DataFrame:
    """
    Extract 2-3 lab values from labevents table.

    Args:
        labevents: Lab events DataFrame
        icustays: ICU stays DataFrame

    Returns:
        DataFrame with features per stay_id
    """
    print("Extracting labevents features...")

    # Get relevant itemids
    relevant_itemids = [
        LABEVENTS_ITEMIDS["lactate"],
        LABEVENTS_ITEMIDS["creatinine"],
    ] + LABEVENTS_ITEMIDS["wbc"]

    labevents_filtered = labevents[labevents["itemid"].isin(relevant_itemids)].copy()

    # Merge with icustays via admissions
    # First need to get hadm_id from icustays
    icustays_with_hadm = icustays[["stay_id", "hadm_id", "intime"]].copy()

    # Labevents links via hadm_id, then we need to link to stay_id
    labevents_merged = labevents_filtered.merge(
        icustays_with_hadm, on="hadm_id", how="inner"
    )

    # Convert charttime to datetime
    labevents_merged["charttime"] = pd.to_datetime(labevents_merged["charttime"])
    labevents_merged["intime"] = pd.to_datetime(labevents_merged["intime"])

    # Filter to first 24 hours of ICU stay
    labevents_merged = labevents_merged[
        (labevents_merged["charttime"] >= labevents_merged["intime"])
        & (
            labevents_merged["charttime"]
            <= labevents_merged["intime"] + pd.Timedelta(hours=24)
        )
    ]

    # Extract numeric values
    labevents_merged["valuenum"] = pd.to_numeric(
        labevents_merged["valuenum"], errors="coerce"
    )

    # Aggregate by stay_id and itemid
    features = []

    for stay_id in icustays["stay_id"].unique():
        stay_data = labevents_merged[labevents_merged["stay_id"] == stay_id]

        feature_row = {"stay_id": stay_id}

        # WBC (check both itemids)
        wbc_data = stay_data[stay_data["itemid"].isin(LABEVENTS_ITEMIDS["wbc"])][
            "valuenum"
        ]
        feature_row["wbc"] = wbc_data.mean() if not wbc_data.empty else np.nan

        # Lactate
        lactate_data = stay_data[stay_data["itemid"] == LABEVENTS_ITEMIDS["lactate"]][
            "valuenum"
        ]
        feature_row["lactate"] = (
            lactate_data.mean() if not lactate_data.empty else np.nan
        )

        # Creatinine
        creatinine_data = stay_data[
            stay_data["itemid"] == LABEVENTS_ITEMIDS["creatinine"]
        ]["valuenum"]
        feature_row["creatinine"] = (
            creatinine_data.mean() if not creatinine_data.empty else np.nan
        )

        features.append(feature_row)

    return pd.DataFrame(features)


def extract_demographics(
    patients: pd.DataFrame, admissions: pd.DataFrame, icustays: pd.DataFrame
) -> pd.DataFrame:
    """
    Extract age and gender from patients table.

    Args:
        patients: Patients DataFrame
        admissions: Admissions DataFrame (not used, kept for compatibility)
        icustays: ICU stays DataFrame

    Returns:
        DataFrame with demographics per stay_id
    """
    print("Extracting demographics...")

    # icustays already has subject_id, so merge directly with patients
    icustays_with_patient = icustays[["stay_id", "subject_id"]].merge(
        patients[["subject_id", "gender", "anchor_age"]], on="subject_id", how="left"
    )

    # Use anchor_age if available, otherwise calculate from anchor_year and anchor_age
    # For demo data, anchor_age should be available
    demographics = icustays_with_patient[["stay_id", "anchor_age", "gender"]].copy()
    demographics.rename(columns={"anchor_age": "age"}, inplace=True)

    # Encode gender (M=1, F=0)
    demographics["gender_encoded"] = (demographics["gender"] == "M").astype(int)

    return demographics[["stay_id", "age", "gender_encoded"]]


def extract_sepsis_labels(
    diagnoses_icd: pd.DataFrame, icustays: pd.DataFrame
) -> pd.DataFrame:
    """
    Extract sepsis labels from diagnoses_icd table.
    Checks both ICD-9 and ICD-10 codes to maximize positive samples.

    Args:
        diagnoses_icd: Diagnoses ICD DataFrame
        icustays: ICU stays DataFrame

    Returns:
        DataFrame with sepsis labels per stay_id
    """
    print("Extracting sepsis labels...")

    # Check what ICD versions are available
    icd_versions = diagnoses_icd["icd_version"].unique()
    print(f"  Available ICD versions: {sorted(icd_versions)}")

    all_sepsis_diagnoses = []

    # Check ICD-10 codes
    if 10 in icd_versions:
        diagnoses_icd10 = diagnoses_icd[diagnoses_icd["icd_version"] == 10].copy()
        print(f"  ICD-10 diagnoses: {len(diagnoses_icd10)} rows")

        sepsis_mask = pd.Series(
            [False] * len(diagnoses_icd10), index=diagnoses_icd10.index
        )

        for code in SEPSIS_ICD10_CODES:
            if "." not in code or code.endswith("."):
                # Pattern match (e.g., "A40" matches "A40.x")
                code_prefix = code.rstrip(".")
                mask = diagnoses_icd10["icd_code"].str.startswith(code_prefix, na=False)
                sepsis_mask |= mask
                if mask.sum() > 0:
                    print(
                        f"    Found {mask.sum()} ICD-10 diagnoses matching pattern '{code}'"
                    )
            else:
                # Exact match
                mask = diagnoses_icd10["icd_code"] == code
                sepsis_mask |= mask
                if mask.sum() > 0:
                    print(
                        f"    Found {mask.sum()} ICD-10 diagnoses with exact code '{code}'"
                    )

        sepsis_icd10 = diagnoses_icd10[sepsis_mask].copy()
        if len(sepsis_icd10) > 0:
            all_sepsis_diagnoses.append(sepsis_icd10)
            print(f"  Total ICD-10 sepsis diagnoses: {len(sepsis_icd10)}")

    # Check ICD-9 codes
    if 9 in icd_versions:
        diagnoses_icd9 = diagnoses_icd[diagnoses_icd["icd_version"] == 9].copy()
        print(f"  ICD-9 diagnoses: {len(diagnoses_icd9)} rows")

        sepsis_mask = pd.Series(
            [False] * len(diagnoses_icd9), index=diagnoses_icd9.index
        )

        for code in SEPSIS_ICD9_CODES:
            if len(code) <= 3 or code.endswith("."):
                # Pattern match (e.g., "038" matches "038.x")
                code_prefix = code.rstrip(".")
                mask = diagnoses_icd9["icd_code"].str.startswith(code_prefix, na=False)
                sepsis_mask |= mask
                if mask.sum() > 0:
                    print(
                        f"    Found {mask.sum()} ICD-9 diagnoses matching pattern '{code}'"
                    )
            else:
                # Exact match
                mask = diagnoses_icd9["icd_code"] == code
                sepsis_mask |= mask
                if mask.sum() > 0:
                    print(
                        f"    Found {mask.sum()} ICD-9 diagnoses with exact code '{code}'"
                    )

        sepsis_icd9 = diagnoses_icd9[sepsis_mask].copy()
        if len(sepsis_icd9) > 0:
            all_sepsis_diagnoses.append(sepsis_icd9)
            print(f"  Total ICD-9 sepsis diagnoses: {len(sepsis_icd9)}")

    # Combine all sepsis diagnoses
    if all_sepsis_diagnoses:
        sepsis_diagnoses = pd.concat(all_sepsis_diagnoses, ignore_index=True)
        print(f"  Total sepsis diagnoses (ICD-9 + ICD-10): {len(sepsis_diagnoses)}")

        if len(sepsis_diagnoses) > 0:
            print(
                f"  Sample sepsis ICD codes: {sepsis_diagnoses['icd_code'].unique()[:15].tolist()}"
            )
            print(
                f"  Unique hadm_id with sepsis: {sepsis_diagnoses['hadm_id'].nunique()}"
            )
    else:
        sepsis_diagnoses = pd.DataFrame(columns=diagnoses_icd.columns)
        print("  No sepsis diagnoses found")

    # Merge with icustays to get stay_id
    icustays_with_hadm = icustays[["stay_id", "hadm_id"]].copy()

    if len(sepsis_diagnoses) > 0:
        sepsis_labels = icustays_with_hadm.merge(
            sepsis_diagnoses[["hadm_id"]].drop_duplicates(),
            on="hadm_id",
            how="left",
            indicator=True,
        )
    else:
        sepsis_labels = icustays_with_hadm.copy()
        sepsis_labels["_merge"] = "left_only"

    # Create binary label (1 if sepsis, 0 otherwise)
    sepsis_labels["sepsis"] = (sepsis_labels["_merge"] == "both").astype(int)

    sepsis_count = sepsis_labels["sepsis"].sum()
    print(
        f"  ICU stays with sepsis: {sepsis_count}/{len(sepsis_labels)} ({sepsis_count/len(sepsis_labels)*100:.2f}%)"
    )

    return sepsis_labels[["stay_id", "sepsis"]]


def print_feature_summary(X: pd.DataFrame):
    """Print feature statistics with FHIR mapping information.

    Args:
        X: Feature matrix with actual data
    """
    print("\n" + "=" * 120)
    print("FEATURE SUMMARY: MIMIC-IV → Model → FHIR Mapping")
    print("=" * 120)

    # Define FHIR mappings for each feature
    fhir_mappings = {
        "heart_rate": {
            "mimic_table": "chartevents",
            "mimic_itemid": "220050",
            "fhir_resource": "Observation",
            "fhir_code": "8867-4",
            "fhir_system": "LOINC",
            "fhir_display": "Heart rate",
        },
        "temperature": {
            "mimic_table": "chartevents",
            "mimic_itemid": "223762/223761",
            "fhir_resource": "Observation",
            "fhir_code": "8310-5",
            "fhir_system": "LOINC",
            "fhir_display": "Body temperature",
        },
        "respiratory_rate": {
            "mimic_table": "chartevents",
            "mimic_itemid": "220210",
            "fhir_resource": "Observation",
            "fhir_code": "9279-1",
            "fhir_system": "LOINC",
            "fhir_display": "Respiratory rate",
        },
        "wbc": {
            "mimic_table": "labevents",
            "mimic_itemid": "51300/51301",
            "fhir_resource": "Observation",
            "fhir_code": "6690-2",
            "fhir_system": "LOINC",
            "fhir_display": "Leukocytes [#/volume] in Blood",
        },
        "lactate": {
            "mimic_table": "labevents",
            "mimic_itemid": "50813",
            "fhir_resource": "Observation",
            "fhir_code": "2524-7",
            "fhir_system": "LOINC",
            "fhir_display": "Lactate [Moles/volume] in Blood",
        },
        "creatinine": {
            "mimic_table": "labevents",
            "mimic_itemid": "50912",
            "fhir_resource": "Observation",
            "fhir_code": "2160-0",
            "fhir_system": "LOINC",
            "fhir_display": "Creatinine [Mass/volume] in Serum or Plasma",
        },
        "age": {
            "mimic_table": "patients",
            "mimic_itemid": "anchor_age",
            "fhir_resource": "Patient",
            "fhir_code": "birthDate",
            "fhir_system": "FHIR Core",
            "fhir_display": "Patient birth date (calculate age)",
        },
        "gender_encoded": {
            "mimic_table": "patients",
            "mimic_itemid": "gender",
            "fhir_resource": "Patient",
            "fhir_code": "gender",
            "fhir_system": "FHIR Core",
            "fhir_display": "Administrative Gender (M/F)",
        },
    }

    print(
        f"\n{'Feature':<20} {'Mean±SD':<20} {'MIMIC Source':<20} {'FHIR Resource':<20} {'FHIR Code (System)':<30}"
    )
    print("-" * 120)

    for feature in X.columns:
        mapping = fhir_mappings.get(feature, {})

        # Calculate statistics
        mean_val = X[feature].mean()
        std_val = X[feature].std()

        # Format based on feature type
        if feature == "gender_encoded":
            stats = f"{mean_val:.2f} (M={X[feature].sum():.0f})"
        else:
            stats = f"{mean_val:.2f}±{std_val:.2f}"

        mimic_source = f"{mapping.get('mimic_table', 'N/A')} ({mapping.get('mimic_itemid', 'N/A')})"
        fhir_resource = mapping.get("fhir_resource", "N/A")
        fhir_code = (
            f"{mapping.get('fhir_code', 'N/A')} ({mapping.get('fhir_system', 'N/A')})"
        )

        print(
            f"{feature:<20} {stats:<20} {mimic_source:<20} {fhir_resource:<20} {fhir_code:<30}"
        )

    print("\n" + "=" * 120)
    print(
        "Note: Statistics calculated from first 24 hours of ICU stay. Missing values imputed with median."
    )
    print("=" * 120 + "\n")


def create_feature_matrix(
    chartevents_features: pd.DataFrame,
    labevents_features: pd.DataFrame,
    demographics: pd.DataFrame,
    sepsis_labels: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Create feature matrix and labels from extracted features.

    Args:
        chartevents_features: Chart events features
        labevents_features: Lab events features
        demographics: Demographics features
        sepsis_labels: Sepsis labels

    Returns:
        Tuple of (feature matrix, labels)
    """
    print("Creating feature matrix...")

    # Merge all features on stay_id
    features = (
        chartevents_features.merge(labevents_features, on="stay_id", how="outer")
        .merge(demographics, on="stay_id", how="outer")
        .merge(sepsis_labels, on="stay_id", how="inner")
    )

    # Select feature columns (exclude stay_id and sepsis)
    feature_cols = [
        "heart_rate",
        "temperature",
        "respiratory_rate",
        "wbc",
        "lactate",
        "creatinine",
        "age",
        "gender_encoded",
    ]

    X = features[feature_cols].copy()
    y = features["sepsis"].copy()

    print(f"Feature matrix shape: {X.shape}")
    print(f"Sepsis cases: {y.sum()} ({y.sum() / len(y) * 100:.2f}%)")

    return X, y


def train_models(X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
    """
    Train all three models (Random Forest, XGBoost, Logistic Regression).

    Args:
        X_train: Training features
        y_train: Training labels

    Returns:
        Dictionary of trained models
    """
    print("\nTraining models...")

    models = {}

    # Check if we have any positive samples
    positive_samples = y_train.sum()
    total_samples = len(y_train)
    positive_rate = positive_samples / total_samples if total_samples > 0 else 0.0

    print(
        f"  Positive samples: {positive_samples}/{total_samples} ({positive_rate*100:.2f}%)"
    )

    # Random Forest - use class_weight to handle imbalance
    print("  Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",  # Automatically adjust for class imbalance
    )
    rf.fit(X_train, y_train)
    models["RandomForest"] = rf

    # XGBoost - handle case with no positive samples
    print("  Training XGBoost...")
    if positive_samples == 0:
        # When there are no positive samples, set base_score to a small value
        # and use scale_pos_weight to avoid errors
        xgb_model = xgb.XGBClassifier(
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
            base_score=0.01,  # Small positive value instead of 0
            scale_pos_weight=1.0,
        )
    else:
        # Calculate scale_pos_weight for imbalanced data
        scale_pos_weight = (total_samples - positive_samples) / positive_samples
        xgb_model = xgb.XGBClassifier(
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
        )
    xgb_model.fit(X_train, y_train)
    models["XGBoost"] = xgb_model

    # Logistic Regression (with scaling) - use class_weight to handle imbalance
    print("  Training Logistic Regression...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    lr = LogisticRegression(
        random_state=42,
        max_iter=1000,
        class_weight="balanced",  # Automatically adjust for class imbalance
    )
    lr.fit(X_train_scaled, y_train)
    models["LogisticRegression"] = lr
    models["scaler"] = scaler  # Store scaler for later use

    return models


def evaluate_models(
    models: Dict[str, Any],
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_names: List[str],
) -> Dict[str, Dict[str, float]]:
    """
    Evaluate and compare all models.

    Args:
        models: Dictionary of trained models
        X_test: Test features
        y_test: Test labels
        feature_names: List of feature names

    Returns:
        Dictionary of evaluation metrics for each model
    """
    print("\nEvaluating models...")
    print(
        f"Test set: {len(y_test)} samples, {y_test.sum()} positive ({y_test.sum()/len(y_test)*100:.2f}%)"
    )

    results = {}

    for name, model in models.items():
        if name == "scaler":
            continue

        # Get probability predictions
        if name == "LogisticRegression":
            X_test_scaled = models["scaler"].transform(X_test)
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            y_pred_proba = model.predict_proba(X_test)[:, 1]

        # Use default threshold (0.5) for predictions
        y_pred = (y_pred_proba >= 0.5).astype(int)

        # Calculate metrics with default threshold
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "auc": roc_auc_score(y_test, y_pred_proba)
            if len(np.unique(y_test)) > 1
            else 0.0,
        }

        # Try to find optimal threshold for F1 score
        if len(np.unique(y_test)) > 1 and y_test.sum() > 0:
            precision, recall, thresholds = precision_recall_curve(y_test, y_pred_proba)
            f1_scores = 2 * (precision * recall) / (precision + recall + 1e-10)
            optimal_idx = np.argmax(f1_scores)
            optimal_threshold = (
                thresholds[optimal_idx] if optimal_idx < len(thresholds) else 0.5
            )
            optimal_f1 = f1_scores[optimal_idx]

            # Predictions with optimal threshold
            y_pred_optimal = (y_pred_proba >= optimal_threshold).astype(int)
            metrics["optimal_threshold"] = optimal_threshold
            metrics["optimal_f1"] = optimal_f1
            metrics["optimal_precision"] = precision_score(
                y_test, y_pred_optimal, zero_division=0
            )
            metrics["optimal_recall"] = recall_score(
                y_test, y_pred_optimal, zero_division=0
            )
        else:
            metrics["optimal_threshold"] = 0.5
            metrics["optimal_f1"] = 0.0
            metrics["optimal_precision"] = 0.0
            metrics["optimal_recall"] = 0.0

        results[name] = metrics

        print(f"\n{name}:")
        print(
            f"  Predictions: {y_pred.sum()} positive predicted (actual: {y_test.sum()})"
        )
        print(f"  Accuracy:  {metrics['accuracy']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall:    {metrics['recall']:.4f}")
        print(f"  F1-score:  {metrics['f1']:.4f}")
        print(f"  AUC-ROC:   {metrics['auc']:.4f}")
        if metrics["optimal_f1"] > 0:
            print(f"  Optimal threshold: {metrics['optimal_threshold']:.4f}")
            print(f"  Optimal F1-score:  {metrics['optimal_f1']:.4f}")
            print(f"  Optimal Precision: {metrics['optimal_precision']:.4f}")
            print(f"  Optimal Recall:    {metrics['optimal_recall']:.4f}")

        # Show feature importance for tree-based models
        if hasattr(model, "feature_importances_"):
            print("\n  Top 5 Feature Importances:")
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1][:5]
            for idx in indices:
                print(f"    {feature_names[idx]}: {importances[idx]:.4f}")

    return results


def select_best_model(
    models: Dict[str, Any],
    results: Dict[str, Dict[str, float]],
    metric: str = "f1",
) -> Tuple[str, Any, Dict[str, float]]:
    """
    Select best model based on specified metric.

    Args:
        models: Dictionary of trained models
        results: Evaluation results
        metric: Metric to optimize ("f1", "recall", "precision", "auc")

    Returns:
        Tuple of (best model name, best model, best metrics)
    """
    print(f"\nSelecting best model based on {metric}...")

    # Get the appropriate metric value (prefer optimal if available)
    def get_metric_value(metrics, metric_name):
        if metric_name == "f1":
            return metrics.get("optimal_f1", metrics["f1"])
        elif metric_name == "recall":
            return metrics.get("optimal_recall", metrics["recall"])
        elif metric_name == "precision":
            return metrics.get("optimal_precision", metrics["precision"])
        elif metric_name == "auc":
            return metrics.get("auc", 0.0)
        else:
            return metrics.get("optimal_f1", metrics["f1"])

    best_name = max(results.keys(), key=lambda k: get_metric_value(results[k], metric))
    best_model = models[best_name]
    best_metrics = results[best_name]

    best_value = get_metric_value(best_metrics, metric)
    print(f"Best model: {best_name} ({metric}: {best_value:.4f})")

    return best_name, best_model, best_metrics


def save_model(
    model: Any,
    model_name: str,
    feature_names: List[str],
    metrics: Dict[str, float],
    scaler: Any,
    output_path: Union[str, Path],
) -> None:
    """
    Save the best model with metadata.

    Args:
        model: Trained model
        model_name: Name of the model
        feature_names: List of feature names
        metrics: Evaluation metrics
        scaler: StandardScaler (if Logistic Regression, None otherwise)
        output_path: Path to save model
    """
    print(f"\nSaving model to {output_path}...")

    # Create output directory if it doesn't exist
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare metadata
    metadata = {
        "model_name": model_name,
        "training_date": datetime.now().isoformat(),
        "feature_names": feature_names,
        "metrics": metrics,
        "itemid_mappings": {
            "chartevents": CHARTEVENTS_ITEMIDS,
            "labevents": LABEVENTS_ITEMIDS,
        },
        "sepsis_icd_codes": {
            "icd10": SEPSIS_ICD10_CODES,
            "icd9": SEPSIS_ICD9_CODES,
        },
    }

    # Save model and metadata
    model_data = {
        "model": model,
        "scaler": scaler,
        "metadata": metadata,
    }

    joblib.dump(model_data, output_path)

    print("Model saved successfully!")


def main():
    """Main training pipeline."""
    # Data directory (set via MIMIC_CSV_PATH or use default)
    data_dir = os.getenv(
        "MIMIC_CSV_PATH", "../datasets/mimic-iv-clinical-database-demo-2.2"
    )

    # Output path (relative to script location)
    script_dir = Path(__file__).parent
    output_path = script_dir / "models" / "sepsis_model.pkl"

    print("=" * 60)
    print("Sepsis Prediction Model Training")
    print("=" * 60)

    # Load data
    tables = load_mimic_data(data_dir)

    # Extract features
    chartevents_features = extract_chartevents_features(
        tables["chartevents"], tables["icustays"]
    )
    labevents_features = extract_labevents_features(
        tables["labevents"], tables["icustays"]
    )
    demographics = extract_demographics(
        tables["patients"], tables["admissions"], tables["icustays"]
    )

    # Extract labels
    sepsis_labels = extract_sepsis_labels(tables["diagnoses_icd"], tables["icustays"])

    # Create feature matrix
    X, y = create_feature_matrix(
        chartevents_features,
        labevents_features,
        demographics,
        sepsis_labels,
    )

    # Handle missing values (impute with median)
    print("\nHandling missing values...")
    missing_before = X.isnull().sum().sum()
    print(f"  Missing values before imputation: {missing_before}")
    X = X.fillna(X.median())

    # Print feature summary with actual data statistics
    print_feature_summary(X)

    # Split data with careful stratification to ensure positive samples in both sets
    print("\nSplitting data...")
    if len(np.unique(y)) > 1 and y.sum() > 0:
        # Use stratification to ensure positive samples in both train and test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print(
            f"  Training set: {len(X_train)} samples ({y_train.sum()} positive, {y_train.sum()/len(y_train)*100:.2f}%)"
        )
        print(
            f"  Test set: {len(X_test)} samples ({y_test.sum()} positive, {y_test.sum()/len(y_test)*100:.2f}%)"
        )

        # Warn if test set has no positive samples (shouldn't happen with stratify, but check anyway)
        if y_test.sum() == 0:
            print(
                "  WARNING: Test set has no positive samples! Consider using a different random seed."
            )
    else:
        print(
            "  Warning: No positive samples or only one class. Skipping stratification."
        )
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        print(f"  Training set: {len(X_train)} samples")
        print(f"  Test set: {len(X_test)} samples")

    # Apply oversampling to training data to balance classes
    print("\nApplying oversampling to training data...")
    try:
        from imblearn.over_sampling import SMOTE

        # Only apply SMOTE if we have positive samples
        if y_train.sum() > 0 and len(np.unique(y_train)) > 1:
            print(
                f"  Before oversampling: {len(X_train)} samples ({y_train.sum()} positive, {y_train.sum()/len(y_train)*100:.2f}%)"
            )
            # Ensure k_neighbors doesn't exceed available positive samples
            k_neighbors = min(5, max(1, y_train.sum() - 1))
            smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
            X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
            print(
                f"  After oversampling: {len(X_train_resampled)} samples ({y_train_resampled.sum()} positive, {y_train_resampled.sum()/len(X_train_resampled)*100:.2f}%)"
            )
            X_train = pd.DataFrame(
                X_train_resampled,
                columns=X_train.columns,
                index=X_train.index[: len(X_train_resampled)],
            )
            y_train = pd.Series(
                y_train_resampled, index=y_train.index[: len(y_train_resampled)]
            )
        else:
            print("  Skipping oversampling: insufficient positive samples")
    except (ImportError, ModuleNotFoundError) as e:
        print(
            "  imbalanced-learn not installed. Install with: pip install imbalanced-learn"
        )
        print(f"  Error: {e}")
        print("  Proceeding without oversampling...")

    # Train models
    models = train_models(X_train, y_train)

    # Evaluate models
    feature_names = X.columns.tolist()
    results = evaluate_models(models, X_test, y_test, feature_names)

    # Select best model (can change metric: "f1", "recall", "precision", "auc")
    # For sepsis prediction, recall (sensitivity) is often most important
    best_name, best_model, best_metrics = select_best_model(
        models, results, metric="f1"
    )

    # Save best model
    scaler = models.get("scaler")
    save_model(
        best_model,
        best_name,
        feature_names,
        best_metrics,
        scaler,
        output_path,
    )

    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
