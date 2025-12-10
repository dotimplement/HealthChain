# Dataset 📊

The `Dataset` is a pandas DataFrame wrapper designed for healthcare ML workflows: it extracts ML-ready features from FHIR Bundles using schemas, validates data types, and converts model predictions back into clinical decision support resources ([RiskAssessment](https://hl7.org/fhir/riskassessment.html)).

## Usage

The two most helpful methods in the `Dataset` class are:

- `from_fhir_bundle()`: Extract ML-ready features from a FHIR Bundle using a feature schema.
- `to_risk_assessment()`: Convert model predictions into FHIR RiskAssessment resources for clinical consumption.

!!! tip "Feature Schemas"
    Define features once in YAML and reuse across training, validation, and inference. See [FHIR Feature Mapper](../mappers/fhir_feature.md) for schema details.


```python
from healthchain.io.containers import Dataset

# 1. Extract ML features from a FHIR Bundle using a feature schema
dataset = Dataset.from_fhir_bundle(bundle, schema="path/to/schema.yaml")

# 2. Inspect the features as a pandas DataFrame
print(dataset.data.head())
print("Columns:", dataset.columns)

# 3. Validate the dataset against the schema (checks for missing/invalid fields)
validation_result = dataset.validate(schema="path/to/schema.yaml")
print("Validation Result:", validation_result)

# 4. Run inference using your ML model and store in metadata
dataset.metadata["predictions"] = model.predict(dataset.data)
dataset.metadata["probabilities"] = model.predict_proba(dataset.data)[:, 1]

# 5. Convert predictions to FHIR RiskAssessment resources for downstream use
risk_assessments = dataset.to_risk_assessment(
    outcome_code="A41.9",
    outcome_display="Sepsis, unspecified",
    model_name="SepsisRiskModel",
    model_version="1.0"
)
```

This workflow lets you convert FHIR healthcare data into DataFrames for ML, and then easily package predictions as standardized FHIR artifacts.


??? example "Example RiskAssessment Output"
    ```json
    {
        "resourceType": "RiskAssessment",
        "id": "hc-a1b2c3d4",
        "status": "final",
        "subject": {
            "reference": "Patient/123"
        },
        "method": {
            "coding": [{
                "system": "https://healthchain.github.io/ml-models",
                "code": "RandomForestClassifier",
                "display": "RandomForestClassifier v2.1"
            }]
        },
        "prediction": [{
            "outcome": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": "A41.9",
                    "display": "Sepsis, unspecified"
                }]
            },
            "probabilityDecimal": 0.85,
            "qualitativeRisk": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/risk-probability",
                    "code": "high",
                    "display": "High Risk"
                }]
            }
        }],
        "note": [{
            "text": "ML prediction: Positive (probability: 85.00%, risk: high)"
        }]
    }
    ```

### Properties and Methods

Common Dataset operations:

```python
# Metadata
print(dataset.columns)           # List of feature names
print(dataset.row_count())       # Number of samples
print(dataset.column_count())    # Number of features
print(dataset.describe())        # Summary statistics

# Data access
df = dataset.data                # Underlying pandas DataFrame
dtypes = dataset.dtypes          # Feature data types

# Data manipulation
dataset.remove_column('temp_feature')  # Drop a feature
```

## Resource Documentation

- [FHIR RiskAssessment](https://www.hl7.org/fhir/riskassessment.html)
- [FHIR Observation](https://www.hl7.org/fhir/observation.html)

## API Reference

See the [Dataset API Reference](../../../api/containers.md#healthchain.io.containers.dataset) for detailed class documentation.
