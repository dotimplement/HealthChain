#!/usr/bin/env python3
"""
Generate a synthetic demo model for the sepsis CDS Hooks cookbook.

Produces cookbook/models/sepsis_model.pkl — a RandomForest trained on
synthetic vitals data with the same feature schema as sepsis_vitals.yaml.

This is a demo artifact for running the cookbook without MIMIC data.
For a model trained on real clinical data, see sepsis_prediction_training.py.

Usage:
    python scripts/generate_demo_model.py
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

FEATURE_NAMES = [
    "heart_rate",
    "temperature",
    "respiratory_rate",
    "wbc",
    "lactate",
    "creatinine",
    "age",
    "gender_encoded",
]

OUTPUT_PATH = Path(__file__).parent.parent / "cookbook" / "models" / "sepsis_model.pkl"

# Demo patient values (from mimic_demo_patients/) used to verify predictions
# after training. The model must score these in the expected risk bands.
DEMO_PATIENTS = {
    "high_risk":     [113, 98.7, 25, 28.5, np.nan, 1.6, np.nan, np.nan],
    "moderate_risk": [70,  99.4, 14, 10.5, np.nan, 1.2, np.nan, np.nan],
    "low_risk":      [110, 98.8, 20,  8.6, np.nan, 0.8, np.nan, np.nan],
}


def generate_training_data(rng: np.random.Generator) -> tuple[pd.DataFrame, pd.Series]:
    """
    Synthetic vitals with clinical plausibility.

    Three groups:
      - Sepsis (y=1): high WBC, elevated RR, raised creatinine
      - Borderline (y=1 ~50%): moderate WBC/creatinine — gives the model
        something to calibrate against for the moderate demo patient
      - Normal (y=0): all values within reference ranges

    Lactate, age, gender are included with realistic ranges but kept weakly
    predictive — the demo patients don't have these values so they will be
    imputed with the median, and they must not dominate predictions.
    """
    n_sepsis = 300
    n_borderline = 200
    n_normal = 500

    def make_group(n, hr, temp, rr, wbc, lactate, creatinine, age, gender):
        return {k: rng.normal(loc=mu, scale=sd, size=n).clip(lo, hi)
                for k, (mu, sd, lo, hi) in zip(FEATURE_NAMES, [
                    hr, temp, rr, wbc, lactate, creatinine, age, gender
                ])}

    sepsis = make_group(
        n_sepsis,
        hr=(115, 20, 80, 160),
        temp=(99.5, 1.5, 96, 104),
        rr=(26, 5, 18, 40),
        wbc=(22, 6, 14, 45),
        lactate=(3.5, 1.2, 2.0, 8.0),
        creatinine=(2.0, 0.5, 1.5, 4.0),
        age=(62, 15, 18, 95),
        gender=(0.55, 0.5, 0, 1),
    )

    # Centred on the moderate demo patient's values (WBC=10.5, creatinine=1.2)
    # so the model treats that region as genuinely ambiguous.
    borderline = make_group(
        n_borderline,
        hr=(88, 15, 65, 120),
        temp=(99.1, 0.8, 97, 101),
        rr=(19, 3, 14, 26),
        wbc=(10.5, 1.5, 8.5, 14),
        lactate=(2.0, 0.6, 1.0, 3.5),
        creatinine=(1.25, 0.15, 1.0, 1.6),
        age=(58, 15, 18, 90),
        gender=(0.5, 0.5, 0, 1),
    )

    # Strictly normal — WBC and creatinine are the key discriminators;
    # HR and RR have wide ranges (tachycardia alone ≠ sepsis) so they
    # don't dominate predictions for the low-risk demo patient (HR=110, RR=20).
    normal = make_group(
        n_normal,
        hr=(82, 18, 55, 120),
        temp=(98.4, 0.8, 96, 100.5),
        rr=(15, 3, 10, 22),
        wbc=(6.8, 1.5, 4, 9.5),
        lactate=(1.1, 0.3, 0.5, 2.0),
        creatinine=(0.85, 0.15, 0.5, 1.15),
        age=(50, 18, 18, 90),
        gender=(0.5, 0.5, 0, 1),
    )

    # Sepsis=1; borderline 60% positive (genuinely uncertain); normal=0
    y_sepsis = np.ones(n_sepsis)
    y_borderline = rng.binomial(1, 0.6, n_borderline).astype(float)
    y_normal = np.zeros(n_normal)

    dfs = [
        pd.DataFrame(sepsis),
        pd.DataFrame(borderline),
        pd.DataFrame(normal),
    ]
    X = pd.concat(dfs, ignore_index=True)
    y = pd.Series(np.concatenate([y_sepsis, y_borderline, y_normal]))

    # Round gender to 0/1
    X["gender_encoded"] = X["gender_encoded"].round().clip(0, 1).astype(int)

    return X, y


def verify_demo_predictions(model, median_values):
    """Check that the demo patients score in the expected risk bands."""
    rows = []
    for name, values in DEMO_PATIENTS.items():
        row = [median_values[f] if np.isnan(v) else v
               for f, v in zip(FEATURE_NAMES, values)]
        rows.append(row)

    X_demo = pd.DataFrame(rows, columns=FEATURE_NAMES)
    probs = model.predict_proba(X_demo)[:, 1]

    expected = {"high_risk": (0.7, 1.0), "moderate_risk": (0.3, 0.75), "low_risk": (0.0, 0.45)}
    all_ok = True
    for (name, prob), (lo, hi) in zip(zip(DEMO_PATIENTS, probs), expected.values()):
        band = "high" if prob > 0.7 else "moderate" if prob > 0.4 else "low"
        ok = lo <= prob <= hi
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {prob:.2f} ({band})")
        if not ok:
            all_ok = False
            print(f"    expected {lo:.2f}–{hi:.2f}")

    return all_ok


def main():
    rng = np.random.default_rng(42)

    print("Generating synthetic training data...")
    X, y = generate_training_data(rng)
    print(f"  {len(X)} samples, {int(y.sum())} positive ({y.mean()*100:.1f}%)")

    print("Training RandomForest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)

    median_values = X.median().to_dict()

    print("\nVerifying demo patient predictions:")
    ok = verify_demo_predictions(model, median_values)
    if not ok:
        print("\nWARNING: Some predictions outside expected range.")
        print("The cookbook will still work but risk bands may not match labels.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "metadata": {
                "model_name": "RandomForest",
                "feature_names": FEATURE_NAMES,
                "metrics": {"optimal_threshold": 0.4},
                "note": "Synthetic demo model — not trained on real patient data.",
            },
        },
        OUTPUT_PATH,
    )

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved to {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
