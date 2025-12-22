#!/usr/bin/env python3
"""
Demo Model Training Script

Creates a sample trained model for demonstration purposes.
In production, replace this with your actual trained model.

Requirements:
    pip install scikit-learn joblib numpy pandas

Run:
    python ml-app/train_demo_model.py
"""

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

# Configuration
SCRIPT_DIR = Path(__file__).parent
MODEL_PATH = SCRIPT_DIR / "models" / "model.pkl"
FEATURE_NAMES = [
    "heart_rate",
    "systolic_bp",
    "respiratory_rate",
    "temperature",
    "oxygen_saturation",
    "age"
]


def generate_synthetic_data(n_samples: int = 1000, random_state: int = 42):
    """Generate synthetic healthcare data for demo model training."""
    np.random.seed(random_state)

    # Generate realistic vital signs
    data = {
        # Heart rate: 60-100 normal, higher in positive cases
        "heart_rate": np.where(
            np.random.rand(n_samples) > 0.5,
            np.random.normal(95, 15, n_samples),  # Higher risk
            np.random.normal(75, 10, n_samples)   # Normal
        ),
        # Systolic BP: 90-140 normal
        "systolic_bp": np.where(
            np.random.rand(n_samples) > 0.5,
            np.random.normal(130, 20, n_samples),  # Higher risk
            np.random.normal(115, 12, n_samples)   # Normal
        ),
        # Respiratory rate: 12-20 normal
        "respiratory_rate": np.where(
            np.random.rand(n_samples) > 0.5,
            np.random.normal(22, 5, n_samples),   # Higher risk
            np.random.normal(16, 3, n_samples)    # Normal
        ),
        # Temperature: 36.1-37.2 normal (Celsius)
        "temperature": np.where(
            np.random.rand(n_samples) > 0.5,
            np.random.normal(38.5, 1, n_samples),  # Fever
            np.random.normal(36.8, 0.4, n_samples)  # Normal
        ),
        # Oxygen saturation: 95-100 normal
        "oxygen_saturation": np.where(
            np.random.rand(n_samples) > 0.5,
            np.random.normal(92, 4, n_samples),   # Lower
            np.random.normal(97, 2, n_samples)    # Normal
        ),
        # Age: 18-90
        "age": np.random.randint(18, 90, n_samples)
    }

    # Generate labels based on feature combinations (simplified risk model)
    risk_score = (
        (data["heart_rate"] > 90).astype(float) * 0.2 +
        (data["systolic_bp"] > 140).astype(float) * 0.15 +
        (data["respiratory_rate"] > 20).astype(float) * 0.25 +
        (data["temperature"] > 37.5).astype(float) * 0.25 +
        (data["oxygen_saturation"] < 95).astype(float) * 0.25 +
        (data["age"] > 65).astype(float) * 0.1
    )

    # Add noise and create binary labels
    risk_score += np.random.normal(0, 0.1, n_samples)
    labels = (risk_score > 0.4).astype(int)

    # Create feature matrix
    X = np.column_stack([data[f] for f in FEATURE_NAMES])

    return X, labels, data


def train_model(X, y, model_type: str = "random_forest"):
    """Train a model on the data."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    if model_type == "random_forest":
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
    else:
        model = LogisticRegression(
            max_iter=1000,
            random_state=42
        )

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
        "optimal_threshold": 0.5
    }

    return model, metrics


def save_model(model, metrics, feature_names, output_path: Path):
    """Save model with metadata in the expected format."""
    model_data = {
        "model": model,
        "metadata": {
            "feature_names": feature_names,
            "metrics": metrics,
            "threshold": metrics.get("optimal_threshold", 0.5),
            "model_type": type(model).__name__,
            "version": "1.0.0"
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_data, output_path)
    print(f"Model saved to: {output_path}")


def main():
    print("="*60)
    print("Demo Model Training")
    print("="*60)

    # Generate data
    print("\nGenerating synthetic healthcare data...")
    X, y, data = generate_synthetic_data(n_samples=2000)
    print(f"  Samples: {len(y)}")
    print(f"  Features: {FEATURE_NAMES}")
    print(f"  Positive rate: {y.mean():.1%}")

    # Train model
    print("\nTraining Random Forest model...")
    model, metrics = train_model(X, y, model_type="random_forest")

    print("\nModel Performance:")
    print(f"  Accuracy:  {metrics['accuracy']:.3f}")
    print(f"  Precision: {metrics['precision']:.3f}")
    print(f"  Recall:    {metrics['recall']:.3f}")
    print(f"  F1 Score:  {metrics['f1']:.3f}")
    print(f"  ROC AUC:   {metrics['roc_auc']:.3f}")

    # Save model
    print("\nSaving model...")
    save_model(model, metrics, FEATURE_NAMES, MODEL_PATH)

    print("\n" + "="*60)
    print("Demo model training complete!")
    print("="*60)
    print(f"\nTo use this model, run:")
    print(f"  python ml-app/app.py")


if __name__ == "__main__":
    main()
