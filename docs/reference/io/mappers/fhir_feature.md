# FHIR Feature Mapper

The `FHIRFeatureMapper` allows you to easily extract relevant features from FHIR Bundles based on a declarative schema. This makes it simple to generate ML-ready DataFrames for downstream analysis and modeling.

## Overview

The mapper uses feature schemas—YAML configs that define which clinical data to extract and how to transform it. This enables:

- **Declarative mapping**: Define features in YAML, not code
- **Reproducible pipelines**: Same schema = same features across train/test/prod
- **Built-in validation**: Type checking catches mismatches before inference
- **FHIR-native**: Works with any EHR's FHIR Bundle

## Usage

Write a YAML file specifying which FHIR resources and codes to extract, desired data types, and any transformations:

```yaml
name: sepsis_prediction_features
version: "1.0"
description: Feature schema for sepsis risk model

# Optional: Control how patient age is calculated
metadata:
  age_calculation: event_date        # Calculate age at event time
  event_date_source: Observation     # Use earliest observation date
  event_date_strategy: earliest

features:
  # Vital signs from Observations
  heart_rate:
    fhir_resource: Observation
    code: "220045"                   # MIMIC-IV itemID
    code_system: http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items
    display: Heart Rate
    unit: bpm
    dtype: float64
    required: true

  # Demographics from Patient resource
  age:
    fhir_resource: Patient
    field: birthDate             # Extract this field
    transform: calculate_age     # Apply this transformation
    dtype: int64
    required: true
```

### Standalone Use

In most cases you should use the [**Dataset**](../containers/dataset.md) API to automatically load your schema and extract features. It's the easiest and most robust workflow.

For advanced usage, you can load a schema and use the `FHIRFeatureMapper` directly for more control:

```python
from healthchain.io.mappers import FHIRFeatureMapper
from healthchain.io.containers import FeatureSchema

# Manually load your YAML feature schema
schema = FeatureSchema.from_yaml("configs/features/my_model.yaml")

# Create the feature mapper with your schema
mapper = FHIRFeatureMapper(schema)

# Extract features from a FHIR Bundle
features_df = mapper.map(bundle, aggregation="mean")

print(features_df.head())
# (Optional) Access patient references
patient_refs = features_df["patient_ref"].tolist()
```

### Aggregation Strategies

When a patient has multiple observations for the same code (e.g., multiple temperature readings), specify how to aggregate them:

```python
# Take the mean of all values
dataset = Dataset.from_fhir_bundle(bundle, schema, aggregation="mean")

# Use the most recent value
dataset = Dataset.from_fhir_bundle(bundle, schema, aggregation="last")

# Other options: "median", "max", "min"
```

### Multiple Code Systems

Different EHRs use different code systems. You can map the same clinical concept across systems:

```yaml
# LOINC code for heart rate (standard)
heart_rate_loinc:
  fhir_resource: Observation
  code: "8867-4"
  code_system: http://loinc.org
  display: Heart Rate
  dtype: float64

# MIMIC-IV internal code
heart_rate_mimic:
  fhir_resource: Observation
  code: "220045"
  code_system: http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items
  display: Heart Rate
  dtype: float64
```

Then in your code, merge as needed:

```python
df = dataset.data
# Combine both columns, preferring LOINC
df['heart_rate'] = df['heart_rate_loinc'].fillna(df['heart_rate_mimic'])
```

### Validation and Error Handling

Check that incoming data matches your training schema:

```python
from healthchain.io.containers import FeatureSchema

schema = FeatureSchema.from_yaml("configs/features/my_model.yaml")
result = dataset.validate(schema, raise_on_error=False)
```

## Related Documentation

- [Dataset Container](../containers/dataset.md) - Complete Dataset API reference
- [Mappers Overview](mappers.md) - Other mapper types
- [FHIR Helpers](../../utilities/fhir_helpers.md) - Creating FHIR resources
