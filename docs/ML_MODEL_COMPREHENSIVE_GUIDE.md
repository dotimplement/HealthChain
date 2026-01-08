# HealthChain ML Model Comprehensive Guide

> Complete technical and business documentation for machine learning model development, deployment, and operations within the HealthChain healthcare AI framework.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technical Summary](#technical-summary)
3. [Business Summary](#business-summary)
4. [Model Lifecycle Guidelines](#model-lifecycle-guidelines)
5. [Testing Strategy](#testing-strategy)
6. [Production Deployment](#production-deployment)
7. [Enhancement Roadmap](#enhancement-roadmap)
8. [Appendix](#appendix)

---

## Executive Summary

HealthChain provides a production-ready framework for deploying machine learning models as healthcare APIs with native FHIR support, CDS Hooks integration, and enterprise-grade security. This guide covers the complete ML lifecycle from data preparation to production deployment.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **FHIR Native** | Direct ingestion of FHIR Bundles with schema-based feature extraction |
| **Real-Time CDS** | Sub-200ms clinical decision support integration |
| **Multi-Source** | Aggregate data from Epic, Cerner, Medplum, and custom FHIR servers |
| **Enterprise Security** | OAuth2/JWT authentication with Auth0, Okta, Azure AD support |
| **Pipeline Architecture** | Composable, type-safe ML pipelines with validation |

### Time-to-Production Comparison

| Approach | Timeline | Effort |
|----------|----------|--------|
| Custom Integration | 2-3 months | High |
| HealthChain Framework | 1-2 weeks | Low |
| **Time Saved** | **80%** | - |

---

## Technical Summary

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      HealthChain ML Platform                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   EHR/EMR    │    │  FHIR Server │    │  CDS Client  │       │
│  │  (Epic,      │    │  (Medplum,   │    │  (EHR Hook   │       │
│  │   Cerner)    │    │   HAPI)      │    │   Trigger)   │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    FHIR Gateway Layer                     │   │
│  │  • Multi-source connectivity (OAuth2, API Key, Basic)    │   │
│  │  • Bundle aggregation and merging                         │   │
│  │  • Patient data retrieval and caching                     │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Feature Extraction Layer                  │   │
│  │  • YAML-based Feature Schema definitions                  │   │
│  │  • FHIR → DataFrame conversion                            │   │
│  │  • LOINC/SNOMED code mapping                              │   │
│  │  • Aggregation (mean, median, last, max, min)             │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    ML Pipeline Layer                      │   │
│  │  • Composable pipeline nodes                              │   │
│  │  • Feature validation and imputation                      │   │
│  │  • Model inference execution                              │   │
│  │  • Risk stratification                                    │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Output Layer                            │   │
│  │  • CDS Cards (real-time alerts)                           │   │
│  │  • FHIR RiskAssessment resources                          │   │
│  │  • JSON/REST API responses                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Dataset Container

The `Dataset` class provides a lightweight wrapper for ML data operations:

```python
from healthchain.io import Dataset

# From FHIR Bundle
dataset = Dataset.from_fhir_bundle(
    bundle,
    schema="schemas/features.yaml",
    aggregation="mean"
)

# From DataFrame
dataset = Dataset.from_dict({
    "age": [45, 67, 32],
    "glucose": [120, 185, 95]
})

# Properties
dataset.columns       # Feature names
dataset.row_count()   # Sample count
dataset.dtypes        # Data type mapping
```

#### 2. Feature Schema System

Declarative YAML-based feature extraction:

```yaml
# schemas/features.yaml
name: healthcare_risk_features
version: "1.0"

model_info:
  model_type: Random Forest Classifier
  target: Risk Assessment
  prediction_window: Point-in-time

features:
  heart_rate:
    fhir_resource: Observation
    code: "8867-4"
    code_system: http://loinc.org
    dtype: float64
    required: true

  age:
    fhir_resource: Patient
    field: birthDate
    transform: calculate_age
    dtype: int64
    required: true

  glucose_fasting:
    fhir_resource: Observation
    code: "1558-6"
    code_system: http://loinc.org
    dtype: float64
    required: false
    default: null
```

#### 3. Pipeline System

Type-safe, composable processing pipelines:

```python
from healthchain.pipeline import Pipeline
from healthchain.io import Dataset

pipeline = Pipeline[Dataset]()

@pipeline.add_node(stage="preprocessing")
def validate_features(dataset: Dataset) -> Dataset:
    """Validate required features are present."""
    missing = set(REQUIRED_FEATURES) - set(dataset.columns)
    if missing:
        raise ValueError(f"Missing features: {missing}")
    return dataset

@pipeline.add_node(stage="preprocessing")
def impute_missing(dataset: Dataset) -> Dataset:
    """Handle missing values with median imputation."""
    dataset.data = dataset.data.fillna(
        dataset.data.median(numeric_only=True)
    )
    return dataset

@pipeline.add_node(stage="inference")
def run_prediction(dataset: Dataset) -> Dataset:
    """Execute model inference."""
    features = dataset.data[FEATURE_NAMES]
    probabilities = model.predict_proba(features)[:, 1]
    dataset.metadata["probabilities"] = probabilities
    dataset.metadata["risk_levels"] = [
        "high" if p >= 0.7 else "moderate" if p >= 0.4 else "low"
        for p in probabilities
    ]
    return dataset

# Execute pipeline
result = pipeline(dataset)
```

#### 4. Model Serialization Format

Standard model package structure:

```python
import joblib

model_data = {
    "model": trained_model,  # sklearn, XGBoost, LightGBM, etc.
    "metadata": {
        "feature_names": ["heart_rate", "age", "glucose", ...],
        "threshold": 0.5,
        "metrics": {
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "f1": 0.85,
            "roc_auc": 0.92
        },
        "model_type": "RandomForestClassifier",
        "version": "1.0.0",
        "trained_date": "2024-01-15",
        "training_samples": 10000
    }
}

joblib.dump(model_data, "models/model.pkl")
```

### Supported Model Types

| Framework | Model Types | Notes |
|-----------|-------------|-------|
| **scikit-learn** | RandomForest, LogisticRegression, GradientBoosting, SVM | Full support |
| **XGBoost** | XGBClassifier, XGBRegressor | Requires `predict_proba()` |
| **LightGBM** | LGBMClassifier, LGBMRegressor | Requires `predict_proba()` |
| **CatBoost** | CatBoostClassifier | Requires `predict_proba()` |
| **PyTorch** | Custom wrapper required | Must implement sklearn-like interface |
| **TensorFlow** | Custom wrapper required | Must implement sklearn-like interface |

### Risk Stratification

Default thresholds (configurable):

| Risk Level | Probability Range | CDS Indicator |
|------------|-------------------|---------------|
| **High** | ≥ 0.70 | `critical` (red) |
| **Moderate** | 0.40 - 0.69 | `warning` (yellow) |
| **Low** | < 0.40 | `info` (blue) |

---

## Business Summary

### Problem Statement

Healthcare organizations face significant challenges deploying ML models:

1. **Data Fragmentation**: Patient data spread across multiple EHR systems
2. **Integration Complexity**: 6-12 months typical integration timeline
3. **Compliance Requirements**: HIPAA, SOC2, HITRUST certifications
4. **Real-Time Requirements**: Clinical workflows require sub-second responses
5. **Interoperability**: HL7 FHIR, CDS Hooks, CDA standards compliance

### Value Proposition

HealthChain accelerates healthcare ML deployment:

| Metric | Traditional | With HealthChain | Improvement |
|--------|-------------|------------------|-------------|
| Integration Time | 3-6 months | 2-4 weeks | **80% faster** |
| Development Cost | $150-300K | $30-50K | **80% reduction** |
| Time to First Prediction | 6+ months | 1 week | **95% faster** |
| Maintenance Overhead | 2-3 FTEs | 0.5 FTE | **75% reduction** |

### Use Cases

#### 1. Real-Time Clinical Decision Support

**Scenario**: Sepsis early warning system
- **Trigger**: Clinician opens patient chart
- **Response Time**: <200ms
- **Output**: Alert card with risk level and recommendations
- **Integration**: Epic, Cerner CDS Hooks

#### 2. Population Health Screening

**Scenario**: Diabetes risk stratification
- **Trigger**: Scheduled batch job (daily/weekly)
- **Scope**: 10,000+ patients
- **Output**: FHIR RiskAssessment resources
- **Use**: Care gap identification, outreach prioritization

#### 3. Multi-EHR Data Aggregation

**Scenario**: Patient 360 view for care coordination
- **Sources**: Epic, Cerner, independent labs
- **Output**: Unified patient record
- **Use**: Care transitions, referral management

### ROI Analysis

For a mid-size health system (500-bed hospital):

| Category | Annual Value |
|----------|--------------|
| Reduced integration costs | $200,000 |
| Faster time-to-value | $150,000 |
| Reduced adverse events (1% improvement) | $500,000 |
| Operational efficiency | $100,000 |
| **Total Annual Value** | **$950,000** |

### Compliance & Security

| Requirement | HealthChain Capability |
|-------------|------------------------|
| **HIPAA** | Audit logging, encryption, access controls |
| **SOC2** | Authentication, authorization, monitoring |
| **HITRUST** | Security controls framework alignment |
| **FDA** | Audit trail for clinical decisions |

---

## Model Lifecycle Guidelines

### Phase 1: Data Preparation

#### 1.1 Define Feature Schema

Create YAML schema mapping FHIR resources to features:

```yaml
# config/feature_schema.yaml
name: diabetes_risk_features
version: "1.0"

features:
  age:
    fhir_resource: Patient
    field: birthDate
    transform: calculate_age
    dtype: int64
    required: true

  bmi:
    fhir_resource: Observation
    code: "39156-5"  # LOINC: BMI
    code_system: http://loinc.org
    dtype: float64
    required: true
    unit: kg/m2

  glucose_fasting:
    fhir_resource: Observation
    code: "1558-6"  # LOINC: Fasting glucose
    code_system: http://loinc.org
    dtype: float64
    required: true
    aggregation: last  # Use most recent value

  hba1c:
    fhir_resource: Observation
    code: "4548-4"  # LOINC: HbA1c
    code_system: http://loinc.org
    dtype: float64
    required: false
    aggregation: last
```

#### 1.2 Data Collection Sources

| Source | Type | Access Method |
|--------|------|---------------|
| **MIMIC-IV** | ICU data | PhysioNet (free, requires credentialing) |
| **Synthea** | Synthetic patients | Open source generator |
| **Medplum** | FHIR sandbox | Free developer account |
| **Production EHR** | Real patient data | OAuth2 + BAA required |

#### 1.3 Synthetic Data Generation

```python
import numpy as np
import pandas as pd

def generate_synthetic_data(n_samples: int = 1000, seed: int = 42):
    """Generate realistic healthcare training data."""
    np.random.seed(seed)

    # Generate features with realistic distributions
    data = {
        "age": np.random.normal(55, 15, n_samples).clip(18, 90),
        "bmi": np.random.normal(28, 6, n_samples).clip(15, 50),
        "glucose_fasting": np.random.normal(105, 25, n_samples).clip(70, 300),
        "hba1c": np.random.normal(6.0, 1.5, n_samples).clip(4.0, 14.0),
        "systolic_bp": np.random.normal(130, 18, n_samples).clip(90, 200),
        "diastolic_bp": np.random.normal(82, 12, n_samples).clip(50, 130),
    }

    # Generate labels based on clinical criteria
    risk_score = (
        (data["age"] > 45).astype(float) * 0.15 +
        (data["bmi"] > 30).astype(float) * 0.25 +
        (data["glucose_fasting"] > 126).astype(float) * 0.30 +
        (data["hba1c"] > 6.5).astype(float) * 0.20 +
        (data["systolic_bp"] > 140).astype(float) * 0.10
    )

    # Add noise for realism
    risk_score += np.random.normal(0, 0.1, n_samples)
    labels = (risk_score > 0.5).astype(int)

    return pd.DataFrame(data), labels
```

### Phase 2: Model Training

#### 2.1 Training Script Template

```python
#!/usr/bin/env python3
"""
Model Training Script
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, classification_report
)

# Configuration
MODEL_PATH = Path("models/model.pkl")
FEATURE_NAMES = ["age", "bmi", "glucose_fasting", "hba1c", "systolic_bp", "diastolic_bp"]
RANDOM_STATE = 42


def load_training_data():
    """Load and prepare training data."""
    # Option 1: From CSV
    # df = pd.read_csv("data/training_data.csv")

    # Option 2: From FHIR bundles
    # from healthchain.io import Dataset
    # dataset = Dataset.from_fhir_bundle(bundle, schema="config/feature_schema.yaml")

    # Option 3: Synthetic data
    X, y = generate_synthetic_data(n_samples=5000)
    return X, y


def train_model(X: pd.DataFrame, y: np.ndarray):
    """Train the ML model with validation."""

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y
    )

    print(f"Training samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")
    print(f"Positive rate: {y_train.mean():.1%}")

    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc")
    print(f"\nCross-validation ROC-AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")

    # Fit final model
    model.fit(X_train, y_train)

    # Evaluate on test set
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
        "cv_roc_auc_mean": cv_scores.mean(),
        "cv_roc_auc_std": cv_scores.std()
    }

    print("\nTest Set Metrics:")
    print(f"  Accuracy:  {metrics['accuracy']:.3f}")
    print(f"  Precision: {metrics['precision']:.3f}")
    print(f"  Recall:    {metrics['recall']:.3f}")
    print(f"  F1 Score:  {metrics['f1']:.3f}")
    print(f"  ROC-AUC:   {metrics['roc_auc']:.3f}")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Low Risk", "High Risk"]))

    # Feature importance
    importance = pd.DataFrame({
        "feature": FEATURE_NAMES,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)

    print("\nFeature Importance:")
    for _, row in importance.iterrows():
        print(f"  {row['feature']}: {row['importance']:.3f}")

    return model, metrics


def save_model(model, metrics: dict):
    """Save model with metadata."""
    model_data = {
        "model": model,
        "metadata": {
            "feature_names": FEATURE_NAMES,
            "threshold": 0.5,
            "metrics": metrics,
            "model_type": type(model).__name__,
            "version": "1.0.0",
            "trained_date": datetime.now().isoformat(),
            "framework": "scikit-learn"
        }
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_data, MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")


def main():
    print("="*60)
    print("Model Training Pipeline")
    print("="*60)

    # Load data
    print("\nLoading training data...")
    X, y = load_training_data()

    # Train model
    print("\nTraining model...")
    model, metrics = train_model(X, y)

    # Save model
    print("\nSaving model...")
    save_model(model, metrics)

    print("\n" + "="*60)
    print("Training complete!")
    print("="*60)


if __name__ == "__main__":
    main()
```

#### 2.2 Hyperparameter Tuning

```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

param_grid = {
    "n_estimators": [50, 100, 200],
    "max_depth": [5, 10, 15, None],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
    "class_weight": ["balanced", None]
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring="roc_auc",
    n_jobs=-1,
    verbose=1
)

grid_search.fit(X_train, y_train)
print(f"Best parameters: {grid_search.best_params_}")
print(f"Best ROC-AUC: {grid_search.best_score_:.3f}")
```

### Phase 3: Model Deployment

#### 3.1 Create Healthcare API Application

```python
# app.py
from pathlib import Path
import joblib

from healthchain.gateway import CDSHooksService, HealthChainAPI
from healthchain.fhir import prefetch_to_bundle
from healthchain.io import Dataset
from healthchain.models import CDSRequest, CDSResponse
from healthchain.models.responses.cdsresponse import Card
from healthchain.pipeline import Pipeline

# Configuration
MODEL_PATH = Path("models/model.pkl")
SCHEMA_PATH = Path("config/feature_schema.yaml")


class RiskAssessmentAPI:
    """Healthcare ML API with CDS Hooks support."""

    def __init__(self):
        self.model_data = joblib.load(MODEL_PATH)
        self.model = self.model_data["model"]
        self.feature_names = self.model_data["metadata"]["feature_names"]
        self.pipeline = self._create_pipeline()

    def _create_pipeline(self) -> Pipeline[Dataset]:
        """Build inference pipeline."""
        pipeline = Pipeline[Dataset]()
        model = self.model
        feature_names = self.feature_names

        @pipeline.add_node
        def impute_missing(dataset: Dataset) -> Dataset:
            dataset.data = dataset.data.fillna(
                dataset.data.median(numeric_only=True)
            )
            return dataset

        @pipeline.add_node
        def predict(dataset: Dataset) -> Dataset:
            features = dataset.data[
                [f for f in feature_names if f in dataset.columns]
            ]
            probs = model.predict_proba(features)[:, 1]
            dataset.metadata["probabilities"] = probs
            return dataset

        return pipeline

    def assess_risk(self, bundle) -> dict:
        """Run risk assessment on FHIR Bundle."""
        dataset = Dataset.from_fhir_bundle(bundle, schema=str(SCHEMA_PATH))
        result = self.pipeline(dataset)

        prob = float(result.metadata["probabilities"][0])
        risk = "high" if prob >= 0.7 else "moderate" if prob >= 0.4 else "low"

        return {
            "probability": prob,
            "risk_level": risk,
            "features_used": list(dataset.columns)
        }


# Initialize
risk_api = RiskAssessmentAPI()

# Create CDS Hooks Service
cds = CDSHooksService()

@cds.hook("patient-view", id="risk-assessment")
def risk_hook(request: CDSRequest) -> CDSResponse:
    """Real-time risk assessment hook."""
    bundle = prefetch_to_bundle(request.prefetch or {})
    result = risk_api.assess_risk(bundle)

    if result["risk_level"] in ["high", "moderate"]:
        indicator = "critical" if result["risk_level"] == "high" else "warning"
        return CDSResponse(cards=[
            Card(
                summary=f"Risk: {result['risk_level'].upper()} ({result['probability']:.0%})",
                indicator=indicator,
                detail=f"Automated risk assessment based on {len(result['features_used'])} features.",
                source={"label": "HealthChain ML"}
            )
        ])

    return CDSResponse(cards=[])


# Create main application
app = HealthChainAPI(
    title="Risk Assessment API",
    version="1.0.0"
)
app.register_service(cds, path="/cds")


@app.post("/predict")
async def predict(bundle: dict):
    """Direct prediction endpoint."""
    from fhir.resources.bundle import Bundle
    return risk_api.assess_risk(Bundle(**bundle))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app.app, host="0.0.0.0", port=8000)
```

#### 3.2 Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY models/ ./models/
COPY config/ ./config/
COPY healthchain/ ./healthchain/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 3.3 Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-healthcare-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-healthcare-api
  template:
    metadata:
      labels:
        app: ml-healthcare-api
    spec:
      containers:
      - name: api
        image: ml-healthcare-api:1.0.0
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        env:
        - name: OAUTH2_ENABLED
          value: "true"
        - name: OAUTH2_ISSUER
          valueFrom:
            secretKeyRef:
              name: oauth2-config
              key: issuer
---
apiVersion: v1
kind: Service
metadata:
  name: ml-healthcare-api
spec:
  selector:
    app: ml-healthcare-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_model.py
import pytest
import pandas as pd
import numpy as np
from app import RiskAssessmentAPI

@pytest.fixture
def api():
    return RiskAssessmentAPI()

def test_high_risk_prediction(api):
    """High-risk patient should return high probability."""
    high_risk_data = pd.DataFrame([{
        "age": 65,
        "bmi": 35,
        "glucose_fasting": 180,
        "hba1c": 8.5,
        "systolic_bp": 160,
        "diastolic_bp": 100
    }])

    # Create mock bundle or use test bundle
    result = api.assess_risk(create_test_bundle(high_risk_data))

    assert result["probability"] > 0.5
    assert result["risk_level"] in ["high", "moderate"]

def test_low_risk_prediction(api):
    """Low-risk patient should return low probability."""
    low_risk_data = pd.DataFrame([{
        "age": 30,
        "bmi": 22,
        "glucose_fasting": 85,
        "hba1c": 5.2,
        "systolic_bp": 115,
        "diastolic_bp": 75
    }])

    result = api.assess_risk(create_test_bundle(low_risk_data))

    assert result["probability"] < 0.4
    assert result["risk_level"] == "low"

def test_missing_features_handled(api):
    """Missing features should be imputed, not cause errors."""
    partial_data = pd.DataFrame([{
        "age": 50,
        "bmi": 28
        # Missing other features
    }])

    result = api.assess_risk(create_test_bundle(partial_data))

    assert "probability" in result
    assert "risk_level" in result
```

### Integration Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app import app

@pytest.fixture
def client():
    return TestClient(app.app)

def test_cds_discovery(client):
    """CDS Hooks discovery endpoint should list services."""
    response = client.get("/cds/cds-services")
    assert response.status_code == 200

    services = response.json()["services"]
    service_ids = [s["id"] for s in services]
    assert "risk-assessment" in service_ids

def test_cds_hook_invocation(client):
    """CDS Hook should return cards for at-risk patients."""
    request_body = {
        "hookInstance": "test-123",
        "hook": "patient-view",
        "context": {
            "userId": "Practitioner/123",
            "patientId": "Patient/456"
        },
        "prefetch": {
            "patient": {"resourceType": "Patient", "id": "456", "birthDate": "1960-01-01"},
            "observations": {
                "resourceType": "Bundle",
                "entry": [
                    {"resource": {"resourceType": "Observation", "code": {"coding": [{"code": "39156-5"}]}, "valueQuantity": {"value": 35}}}
                ]
            }
        }
    }

    response = client.post("/cds/cds-services/risk-assessment", json=request_body)
    assert response.status_code == 200
    assert "cards" in response.json()

def test_predict_endpoint(client):
    """Direct prediction endpoint should accept FHIR Bundle."""
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "123", "birthDate": "1970-05-15"}}
        ]
    }

    response = client.post("/predict", json=bundle)
    assert response.status_code == 200
    assert "probability" in response.json()
    assert "risk_level" in response.json()
```

### Load Testing

```python
# tests/load_test.py
from locust import HttpUser, task, between

class MLAPIUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(3)
    def predict(self):
        """Test prediction endpoint."""
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "123", "birthDate": "1970-05-15"}}
            ]
        }
        self.client.post("/predict", json=bundle)

    @task(1)
    def health_check(self):
        """Test health endpoint."""
        self.client.get("/health")

# Run: locust -f tests/load_test.py --host=http://localhost:8000
```

### Sandbox Testing

```python
# tests/sandbox_test.py
from healthchain.sandbox import SandboxClient

def test_with_synthetic_patients():
    """Test with sandbox client and synthetic data."""
    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/risk-assessment",
        workflow="patient-view"
    )

    # Load test patients
    client.load_from_path("data/test_patients", pattern="*.json")

    # Send requests
    responses = client.send_requests()

    # Validate responses
    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert "cards" in data

    # Save results for review
    client.save_results(directory="./test_output/")
```

---

## Production Deployment

### Environment Configuration

```bash
# .env.production
# OAuth2 Configuration
OAUTH2_ENABLED=true
OAUTH2_ISSUER=https://auth.example.com
OAUTH2_AUDIENCE=healthcare-api
OAUTH2_JWKS_URI=https://auth.example.com/.well-known/jwks.json

# FHIR Server Configuration
MEDPLUM_CLIENT_ID=your-client-id
MEDPLUM_CLIENT_SECRET=your-client-secret
MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
MEDPLUM_TOKEN_URL=https://api.medplum.com/oauth2/token

# Application Settings
API_TITLE=Risk Assessment API
API_VERSION=1.0.0
LOG_LEVEL=INFO
DEBUG=false

# Risk Thresholds
RISK_THRESHOLD_HIGH=0.7
RISK_THRESHOLD_MODERATE=0.4
```

### Monitoring & Observability

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API Latency (P95) | <200ms | >500ms |
| Error Rate | <0.1% | >1% |
| Availability | 99.9% | <99.5% |
| Model Inference Time | <50ms | >100ms |
| Memory Usage | <80% | >90% |

### Security Checklist

- [ ] OAuth2 authentication enabled
- [ ] HTTPS/TLS configured
- [ ] No PHI in logs
- [ ] Audit logging enabled
- [ ] Rate limiting configured
- [ ] Input validation on all endpoints
- [ ] CORS properly configured
- [ ] Secrets in environment variables (not code)
- [ ] Container runs as non-root user
- [ ] Network policies restrict access

---

## Enhancement Roadmap

### Phase 1: Foundation (Current)

| Feature | Status | Description |
|---------|--------|-------------|
| Random Forest Models | ✅ Complete | Basic sklearn model support |
| FHIR Bundle Ingestion | ✅ Complete | Dataset.from_fhir_bundle() |
| CDS Hooks Integration | ✅ Complete | Real-time clinical alerts |
| OAuth2 Authentication | ✅ Complete | JWT bearer token validation |
| Feature Schema | ✅ Complete | YAML-based feature mapping |

### Phase 2: Model Enhancements (Next 3 months)

| Feature | Priority | Description |
|---------|----------|-------------|
| **XGBoost/LightGBM Support** | High | Native gradient boosting integration |
| **Model Versioning** | High | Multiple model versions with A/B testing |
| **Feature Store Integration** | Medium | Connect to Feast, Tecton |
| **AutoML Pipeline** | Medium | Automated hyperparameter tuning |
| **Explainability (SHAP)** | High | Feature importance explanations |
| **Calibration** | Medium | Probability calibration for better thresholds |

### Phase 3: Advanced Capabilities (6-12 months)

| Feature | Priority | Description |
|---------|----------|-------------|
| **Deep Learning Support** | Medium | PyTorch/TensorFlow model serving |
| **Time Series Models** | High | LSTM/Transformer for longitudinal data |
| **Federated Learning** | Low | Train across institutions without data sharing |
| **Real-Time Retraining** | Medium | Continuous learning from production data |
| **Multi-Task Learning** | Low | Single model for multiple outcomes |
| **Uncertainty Quantification** | Medium | Confidence intervals on predictions |

### Phase 4: Enterprise Features (12+ months)

| Feature | Priority | Description |
|---------|----------|-------------|
| **Model Governance Dashboard** | High | UI for model lifecycle management |
| **Drift Detection** | High | Automated data/concept drift monitoring |
| **Regulatory Reporting** | High | FDA/CE mark documentation generation |
| **Multi-Tenant Support** | Medium | Isolated deployments per organization |
| **Edge Deployment** | Low | Deploy to on-premise/edge devices |

### Technical Debt & Improvements

| Item | Priority | Effort |
|------|----------|--------|
| Increase test coverage to 90% | High | Medium |
| Add async model inference | Medium | Low |
| Implement model caching | Medium | Low |
| Add structured logging | High | Low |
| Performance benchmarking suite | Medium | Medium |
| Documentation improvements | High | Medium |

---

## Appendix

### A. Common LOINC Codes for Features

| Feature | LOINC Code | Description |
|---------|------------|-------------|
| Heart Rate | 8867-4 | Heart rate |
| Systolic BP | 8480-6 | Systolic blood pressure |
| Diastolic BP | 8462-4 | Diastolic blood pressure |
| Respiratory Rate | 9279-1 | Respiratory rate |
| Temperature | 8310-5 | Body temperature |
| Oxygen Saturation | 2708-6 | Oxygen saturation in arterial blood |
| BMI | 39156-5 | Body mass index |
| Glucose (Fasting) | 1558-6 | Fasting glucose |
| HbA1c | 4548-4 | Hemoglobin A1c |
| WBC | 6690-2 | White blood cell count |
| Hemoglobin | 718-7 | Hemoglobin |
| Creatinine | 2160-0 | Creatinine |
| Lactate | 2524-7 | Lactate |

### B. Model Performance Benchmarks

| Model Type | Training Time (10K samples) | Inference Time (per sample) | Memory |
|------------|----------------------------|----------------------------|--------|
| Logistic Regression | 0.5s | 0.1ms | 10MB |
| Random Forest (100 trees) | 5s | 1ms | 50MB |
| XGBoost | 3s | 0.5ms | 30MB |
| LightGBM | 2s | 0.3ms | 25MB |
| Neural Network (small) | 60s | 2ms | 100MB |

### C. Troubleshooting Guide

| Issue | Cause | Solution |
|-------|-------|----------|
| Missing features error | FHIR Bundle lacks required observations | Check feature schema, make features optional |
| Low prediction accuracy | Insufficient training data | Add more samples, balance classes |
| High latency | Large model or slow feature extraction | Optimize pipeline, use lighter model |
| OAuth2 token rejected | Invalid issuer or audience | Verify JWKS URI and audience configuration |
| Memory errors | Model too large for container | Increase memory limits, use lighter model |

### D. References

- [HealthChain Documentation](https://dotimplement.github.io/HealthChain/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [CDS Hooks Specification](https://cds-hooks.org/)
- [MIMIC-IV Dataset](https://physionet.org/content/mimiciv/)
- [Synthea Patient Generator](https://synthetichealth.github.io/synthea/)

---

*Document Version: 1.0.0*
*Last Updated: December 2024*
*Maintainer: HealthChain Team*
