import pytest
import pandas as pd
import numpy as np


from healthchain.io.containers.dataset import Dataset


def test_dataset_from_fhir_bundle(observation_bundle, minimal_schema):
    """Dataset.from_fhir_bundle extracts features using schema."""
    dataset = Dataset.from_fhir_bundle(observation_bundle, minimal_schema)

    assert len(dataset.data) == 1
    assert "patient_ref" in dataset.columns
    assert "heart_rate" in dataset.columns
    assert "temperature" in dataset.columns
    assert "age" in dataset.columns


def test_dataset_from_fhir_bundle_with_yaml_path(observation_bundle):
    """Dataset.from_fhir_bundle accepts YAML schema path."""
    schema_path = "healthchain/configs/features/sepsis_vitals.yaml"
    dataset = Dataset.from_fhir_bundle(observation_bundle, schema_path)

    assert len(dataset.data) == 1
    assert "patient_ref" in dataset.columns


def test_dataset_from_fhir_bundle_with_aggregation(
    observation_bundle_with_duplicates, minimal_schema
):
    """Dataset.from_fhir_bundle respects aggregation parameter."""
    dataset_mean = Dataset.from_fhir_bundle(
        observation_bundle_with_duplicates, minimal_schema, aggregation="mean"
    )
    dataset_max = Dataset.from_fhir_bundle(
        observation_bundle_with_duplicates, minimal_schema, aggregation="max"
    )

    assert dataset_mean.data["heart_rate"].iloc[0] == pytest.approx(87.666667, rel=1e-5)
    assert dataset_max.data["heart_rate"].iloc[0] == 90.0


def test_dataset_validate_with_complete_data(sample_dataset, minimal_schema):
    """Dataset.validate passes with complete valid data."""
    result = sample_dataset.validate(minimal_schema)

    assert result.valid is True
    assert len(result.missing_features) == 0
    assert len(result.errors) == 0


def test_dataset_validate_detects_missing_required_features(
    sample_dataset_incomplete, minimal_schema
):
    """Dataset.validate detects missing required features."""
    result = sample_dataset_incomplete.validate(minimal_schema)

    assert result.valid is False
    assert len(result.missing_features) > 0
    assert "age" in result.missing_features
    assert "gender_encoded" in result.missing_features


def test_dataset_validate_raises_on_error_when_requested(
    sample_dataset_incomplete, minimal_schema
):
    """Dataset.validate raises exception when raise_on_error is True."""
    with pytest.raises(ValueError, match="Validation failed"):
        sample_dataset_incomplete.validate(minimal_schema, raise_on_error=True)


def test_dataset_validate_detects_type_mismatches(
    sample_dataset_wrong_types, minimal_schema
):
    """Dataset.validate detects incorrect data types."""
    result = sample_dataset_wrong_types.validate(minimal_schema)

    # Type mismatches are recorded even if they don't fail validation due to dtype_compatible
    assert len(result.type_mismatches) > 0
    # heart_rate should be object (string) instead of float64
    assert "heart_rate" in result.type_mismatches
    # Check that errors were added for the type mismatches
    assert len(result.errors) > 0
    assert any("heart_rate" in error for error in result.errors)


def test_dataset_validate_warns_about_missing_optional(minimal_schema):
    """Dataset.validate generates warnings for missing optional features."""
    data = pd.DataFrame(
        {
            "patient_ref": ["Patient/1"],
            "heart_rate": [85.0],
            "age": [45],
            "gender_encoded": [1],
            # Missing optional "temperature"
        }
    )
    dataset = Dataset(data)

    result = dataset.validate(minimal_schema)

    assert result.valid is True
    assert len(result.warnings) > 0
    assert any("temperature" in w for w in result.warnings)


def test_dataset_dtype_compatibility_allows_numeric_flexibility():
    """Dataset._dtypes_compatible allows flexibility between numeric types."""
    data = pd.DataFrame(
        {
            "patient_ref": ["Patient/1"],
            "value_int": [45],  # int64
            "value_float": [45.0],  # float64
        }
    )
    dataset = Dataset(data)

    # int64 and float64 should be compatible
    assert dataset._dtypes_compatible("int64", "float64")
    assert dataset._dtypes_compatible("float64", "int64")
    assert dataset._dtypes_compatible("int32", "float64")


def test_dataset_to_risk_assessment_creates_resources(sample_dataset):
    """Dataset.to_risk_assessment creates RiskAssessment resources."""
    predictions = np.array([0, 1])
    probabilities = np.array([0.15, 0.85])

    risks = sample_dataset.to_risk_assessment(
        predictions, probabilities, outcome_code="A41.9", outcome_display="Sepsis"
    )

    assert len(risks) == 2
    assert risks[0].subject.reference == "Patient/1"
    assert risks[1].subject.reference == "Patient/2"
    assert risks[0].status == "final"


def test_dataset_to_risk_assessment_categorizes_risk_levels():
    """Dataset.to_risk_assessment correctly categorizes risk levels."""
    predictions = np.array([0, 1, 0])
    probabilities = np.array([0.15, 0.85, 0.55])  # low, high, moderate

    # Need 3 patients for this test
    data = pd.DataFrame(
        {
            "patient_ref": ["Patient/1", "Patient/2", "Patient/3"],
            "heart_rate": [85.0, 92.0, 88.0],
            "temperature": [37.0, 37.5, 37.2],
            "age": [45, 62, 50],
            "gender_encoded": [1, 0, 1],
        }
    )
    dataset = Dataset(data)

    risks = dataset.to_risk_assessment(
        predictions, probabilities, outcome_code="A41.9", outcome_display="Sepsis"
    )

    # Check qualitative risk levels
    assert risks[0].prediction[0].qualitativeRisk.coding[0].code == "low"
    assert risks[1].prediction[0].qualitativeRisk.coding[0].code == "high"
    assert risks[2].prediction[0].qualitativeRisk.coding[0].code == "moderate"


def test_dataset_to_risk_assessment_includes_probabilities(sample_dataset):
    """Dataset.to_risk_assessment includes probability values."""
    predictions = np.array([0, 1])
    probabilities = np.array([0.25, 0.75])

    risks = sample_dataset.to_risk_assessment(
        predictions, probabilities, outcome_code="A41.9", outcome_display="Sepsis"
    )

    assert risks[0].prediction[0].probabilityDecimal == 0.25
    assert risks[1].prediction[0].probabilityDecimal == 0.75


def test_dataset_to_risk_assessment_includes_model_metadata(sample_dataset):
    """Dataset.to_risk_assessment includes model name and version."""
    predictions = np.array([0, 1])
    probabilities = np.array([0.15, 0.85])

    risks = sample_dataset.to_risk_assessment(
        predictions,
        probabilities,
        outcome_code="A41.9",
        outcome_display="Sepsis",
        model_name="RandomForest",
        model_version="1.0",
    )

    assert risks[0].method is not None
    assert risks[0].method.coding[0].code == "RandomForest"
    assert "v1.0" in risks[0].method.coding[0].display


def test_dataset_to_risk_assessment_requires_matching_lengths(sample_dataset):
    """Dataset.to_risk_assessment validates array lengths match DataFrame."""
    predictions = np.array([0])  # Only 1, but dataset has 2 rows
    probabilities = np.array([0.15, 0.85])

    with pytest.raises(ValueError, match="Predictions length .* must match"):
        sample_dataset.to_risk_assessment(
            predictions, probabilities, outcome_code="A41.9", outcome_display="Sepsis"
        )


def test_dataset_to_risk_assessment_requires_patient_ref_column():
    """Dataset.to_risk_assessment requires patient_ref column."""
    data = pd.DataFrame(
        {
            "heart_rate": [85.0, 92.0],  # Missing patient_ref
            "age": [45, 62],
        }
    )
    dataset = Dataset(data)

    predictions = np.array([0, 1])
    probabilities = np.array([0.15, 0.85])

    with pytest.raises(ValueError, match="DataFrame must have 'patient_ref' column"):
        dataset.to_risk_assessment(
            predictions, probabilities, outcome_code="A41.9", outcome_display="Sepsis"
        )


def test_dataset_to_risk_assessment_with_edge_probabilities():
    """Dataset.to_risk_assessment handles edge probability values correctly."""
    data = pd.DataFrame(
        {"patient_ref": ["Patient/1", "Patient/2", "Patient/3"], "value": [1, 2, 3]}
    )
    dataset = Dataset(data)

    predictions = np.array([0, 1, 0])
    probabilities = np.array([0.0, 1.0, 0.5])  # Edge cases

    risks = dataset.to_risk_assessment(
        predictions, probabilities, outcome_code="A41.9", outcome_display="Sepsis"
    )

    # 0.0 should be low, 1.0 should be high, 0.5 should be moderate
    assert risks[0].prediction[0].qualitativeRisk.coding[0].code == "low"
    assert risks[1].prediction[0].qualitativeRisk.coding[0].code == "high"
    assert risks[2].prediction[0].qualitativeRisk.coding[0].code == "moderate"


def test_dataset_to_risk_assessment_includes_comments(sample_dataset):
    """Dataset.to_risk_assessment generates descriptive comments."""
    predictions = np.array([0, 1])
    probabilities = np.array([0.15, 0.85])

    risks = sample_dataset.to_risk_assessment(
        predictions, probabilities, outcome_code="A41.9", outcome_display="Sepsis"
    )

    # Check comments contain prediction info
    assert risks[0].note is not None
    assert "Negative" in risks[0].note[0].text
    assert "15.00%" in risks[0].note[0].text
    assert "low" in risks[0].note[0].text

    assert "Positive" in risks[1].note[0].text
    assert "85.00%" in risks[1].note[0].text
    assert "high" in risks[1].note[0].text
