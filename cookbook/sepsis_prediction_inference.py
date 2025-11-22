#!/usr/bin/env python3
"""
Sepsis Prediction Inference Script

Demonstrates how to load and use the trained sepsis prediction model.

Requirements:
- pip install scikit-learn xgboost joblib pandas numpy

Usage:
- python sepsis_prediction_inference.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Union, Tuple
import joblib


def load_model(model_path: Union[str, Path]) -> Dict:
    """
    Load trained sepsis prediction model.

    Args:
        model_path: Path to saved model file

    Returns:
        Dictionary containing model, scaler, and metadata
    """
    print(f"Loading model from {model_path}...")
    model_data = joblib.load(model_path)

    metadata = model_data["metadata"]
    print(f"  Model: {metadata['model_name']}")
    print(f"  Training date: {metadata['training_date']}")
    print(f"  Features: {', '.join(metadata['feature_names'])}")
    print(f"  Test F1-score: {metadata['metrics']['f1']:.4f}")
    print(f"  Test AUC-ROC: {metadata['metrics']['auc']:.4f}")

    if "optimal_threshold" in metadata["metrics"]:
        print(f"  Optimal threshold: {metadata['metrics']['optimal_threshold']:.4f}")
        print(f"  Optimal F1-score: {metadata['metrics']['optimal_f1']:.4f}")

    return model_data


def predict_sepsis(
    model_data: Dict, patient_features: pd.DataFrame, use_optimal_threshold: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Predict sepsis risk for patient(s).

    Args:
        model_data: Dictionary containing model, scaler, and metadata
        patient_features: DataFrame with patient features
        use_optimal_threshold: Whether to use optimal threshold (default: True)

    Returns:
        Tuple of (predictions, probabilities)
    """
    model = model_data["model"]
    scaler = model_data["scaler"]
    metadata = model_data["metadata"]
    feature_names = metadata["feature_names"]

    # Ensure features are in correct order
    patient_features = patient_features[feature_names]

    # Apply scaling if Logistic Regression
    if scaler is not None:
        patient_features_scaled = scaler.transform(patient_features)
        probabilities = model.predict_proba(patient_features_scaled)[:, 1]
    else:
        probabilities = model.predict_proba(patient_features)[:, 1]

    # Use optimal threshold if available and requested
    if use_optimal_threshold and "optimal_threshold" in metadata["metrics"]:
        threshold = metadata["metrics"]["optimal_threshold"]
    else:
        threshold = 0.5

    predictions = (probabilities >= threshold).astype(int)

    return predictions, probabilities


def create_example_patients() -> pd.DataFrame:
    """
    Create example patient data for demonstration.

    Returns:
        DataFrame with example patient features
    """
    # Example patient data
    # Patient 1: Healthy patient (low risk)
    # Patient 2: Moderate risk (some abnormal values)
    # Patient 3: Low risk (normal values)
    # Patient 4: High risk for sepsis (multiple severe abnormalities)
    # Patient 5: Critical sepsis risk (severe multi-organ dysfunction)
    patients = pd.DataFrame(
        {
            "heart_rate": [85, 110, 75, 130, 145],  # beats/min (normal: 60-100)
            "temperature": [
                37.2,
                38.5,
                36.8,
                39.2,
                35.5,
            ],  # Celsius (normal: 36.5-37.5, hypothermia <36)
            "respiratory_rate": [16, 24, 14, 30, 35],  # breaths/min (normal: 12-20)
            "wbc": [8.5, 15.2, 7.0, 18.5, 22.0],  # x10^9/L (normal: 4-11)
            "lactate": [
                1.2,
                3.5,
                0.9,
                4.8,
                6.5,
            ],  # mmol/L (normal: <2, severe sepsis: >4)
            "creatinine": [0.9, 1.8, 0.8, 2.5, 3.2],  # mg/dL (normal: 0.6-1.2)
            "age": [45, 68, 35, 72, 78],  # years
            "gender_encoded": [1, 0, 1, 1, 0],  # 1=Male, 0=Female
        }
    )

    return patients


def interpret_results(
    predictions: np.ndarray, probabilities: np.ndarray, patient_features: pd.DataFrame
) -> None:
    """
    Interpret and display prediction results.

    Args:
        predictions: Binary predictions (0=no sepsis, 1=sepsis)
        probabilities: Probability scores
        patient_features: Original patient features
    """
    print("\n" + "=" * 80)
    print("SEPSIS PREDICTION RESULTS")
    print("=" * 80)

    for i in range(len(predictions)):
        print(f"\nPatient {i+1}:")
        print(f"  Risk Score: {probabilities[i]:.2%}")
        print(f"  Prediction: {'SEPSIS RISK' if predictions[i] == 1 else 'Low Risk'}")

        # Show key vital signs
        print("  Key Features:")
        print(f"    Heart Rate: {patient_features.iloc[i]['heart_rate']:.1f} bpm")
        print(f"    Temperature: {patient_features.iloc[i]['temperature']:.1f}°C")
        print(
            f"    Respiratory Rate: {patient_features.iloc[i]['respiratory_rate']:.1f} /min"
        )
        print(f"    WBC: {patient_features.iloc[i]['wbc']:.1f} x10^9/L")
        print(f"    Lactate: {patient_features.iloc[i]['lactate']:.1f} mmol/L")
        print(f"    Creatinine: {patient_features.iloc[i]['creatinine']:.2f} mg/dL")

        # Risk interpretation
        if probabilities[i] >= 0.7:
            risk_level = "HIGH"
        elif probabilities[i] >= 0.4:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        print(f"  Clinical Interpretation: {risk_level} RISK")

    print("\n" + "=" * 80)


def main():
    """Main inference pipeline."""
    # Model path (relative to script location)
    script_dir = Path(__file__).parent
    model_path = script_dir / "models" / "sepsis_model.pkl"

    print("=" * 80)
    print("Sepsis Prediction Inference")
    print("=" * 80 + "\n")

    # Load model
    model_data = load_model(model_path)

    # Create example patients
    print("\nCreating example patient data...")
    patient_features = create_example_patients()
    print(f"Number of patients: {len(patient_features)}")

    # Make predictions
    print("\nMaking predictions...")
    predictions, probabilities = predict_sepsis(
        model_data, patient_features, use_optimal_threshold=True
    )

    # Interpret results
    interpret_results(predictions, probabilities, patient_features)

    print("\n" + "=" * 80)
    print("Inference complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
