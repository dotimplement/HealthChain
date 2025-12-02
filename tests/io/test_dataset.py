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


def test_dataset_to_risk_assessment_creates_resources_with_metadata(sample_dataset):
    """Dataset.to_risk_assessment creates RiskAssessment resources with probabilities, model metadata, and comments."""
    predictions = np.array([0, 1])
    probabilities = np.array([0.15, 0.85])

    # Test with model metadata
    sample_dataset.metadata["predictions"] = predictions
    sample_dataset.metadata["probabilities"] = probabilities
    risks = sample_dataset.to_risk_assessment(
        outcome_code="A41.9",
        outcome_display="Sepsis",
        model_name="RandomForest",
        model_version="1.0",
    )

    # Basic structure
    assert len(risks) == 2
    assert risks[0].subject.reference == "Patient/1"
    assert risks[1].subject.reference == "Patient/2"
    assert risks[0].status == "final"

    # Probabilities
    assert risks[0].prediction[0].probabilityDecimal == 0.15
    assert risks[1].prediction[0].probabilityDecimal == 0.85

    # Model metadata
    assert risks[0].method is not None
    assert risks[0].method.coding[0].code == "RandomForest"
    assert "v1.0" in risks[0].method.coding[0].display

    # Comments
    assert risks[0].note is not None
    assert "Negative" in risks[0].note[0].text
    assert "15.00%" in risks[0].note[0].text
    assert "low" in risks[0].note[0].text
    assert "Positive" in risks[1].note[0].text
    assert "85.00%" in risks[1].note[0].text
    assert "high" in risks[1].note[0].text


@pytest.mark.parametrize(
    "predictions,probabilities,expected_risks",
    [
        ([0, 1, 0], [0.15, 0.85, 0.55], ["low", "high", "moderate"]),
        ([0, 1, 0], [0.0, 1.0, 0.5], ["low", "high", "moderate"]),  # Edge cases
    ],
)
def test_dataset_to_risk_assessment_categorizes_risk_levels(
    predictions, probabilities, expected_risks
):
    """Dataset.to_risk_assessment correctly categorizes risk levels including edge probabilities."""
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
    dataset.metadata["predictions"] = np.array(predictions)
    dataset.metadata["probabilities"] = np.array(probabilities)

    risks = dataset.to_risk_assessment(
        outcome_code="A41.9",
        outcome_display="Sepsis",
    )

    for i, expected_risk in enumerate(expected_risks):
        assert risks[i].prediction[0].qualitativeRisk.coding[0].code == expected_risk


@pytest.mark.parametrize(
    "data_dict,predictions,probabilities,expected_error",
    [
        (
            {"heart_rate": [85.0, 92.0], "age": [45, 62]},  # Missing patient_ref
            [0, 1],
            [0.15, 0.85],
            "DataFrame must have 'patient_ref' column",
        ),
        (
            {"patient_ref": ["Patient/1", "Patient/2"], "value": [1, 2]},
            [0],  # Wrong prediction length
            [0.15, 0.85],
            "Predictions length .* must match",
        ),
        (
            {"patient_ref": ["Patient/1", "Patient/2"], "value": [1, 2]},
            [0, 1],
            [0.15],  # Wrong probability length
            "Probabilities length .* must match",
        ),
    ],
)
def test_dataset_to_risk_assessment_validation_errors(
    data_dict, predictions, probabilities, expected_error
):
    """Dataset.to_risk_assessment validates required columns and array lengths."""
    data = pd.DataFrame(data_dict)
    dataset = Dataset(data)
    dataset.metadata["predictions"] = np.array(predictions)
    dataset.metadata["probabilities"] = np.array(probabilities)

    with pytest.raises(ValueError, match=expected_error):
        dataset.to_risk_assessment(
            outcome_code="A41.9",
            outcome_display="Sepsis",
        )


def test_dataset_from_csv_loads_correctly(tmp_path):
    """Dataset.from_csv loads CSV files into DataFrame."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "patient_ref,heart_rate,age\nPatient/1,85.0,45\nPatient/2,92.0,62"
    )

    dataset = Dataset.from_csv(str(csv_file))

    assert len(dataset.data) == 2
    assert "patient_ref" in dataset.columns
    assert dataset.data["heart_rate"].iloc[0] == 85.0


def test_dataset_from_dict_creates_dataframe():
    """Dataset.from_dict creates DataFrame from dict."""
    data_dict = {
        "data": {"patient_ref": ["Patient/1", "Patient/2"], "heart_rate": [85.0, 92.0]}
    }

    dataset = Dataset.from_dict(data_dict)

    assert len(dataset.data) == 2
    assert "patient_ref" in dataset.columns
    assert "heart_rate" in dataset.columns
    assert dataset.data["heart_rate"].iloc[0] == 85.0


def test_dataset_to_csv_saves_correctly(tmp_path, sample_dataset):
    """Dataset.to_csv exports DataFrame to CSV."""
    csv_file = tmp_path / "output.csv"

    sample_dataset.to_csv(str(csv_file), index=False)

    assert csv_file.exists()
    df = pd.read_csv(csv_file)
    assert len(df) == 2
    assert "patient_ref" in df.columns


def test_dataset_rejects_non_dataframe_input():
    """Dataset validates input is a DataFrame in __post_init__."""
    with pytest.raises(TypeError, match="data must be a pandas DataFrame"):
        Dataset([{"patient_ref": "Patient/1"}])


def test_dataset_to_risk_assessment_validates_probability_length():
    """Dataset.to_risk_assessment validates probabilities array length."""
    data = pd.DataFrame({"patient_ref": ["Patient/1", "Patient/2"], "value": [1, 2]})
    dataset = Dataset(data)
    dataset.metadata["predictions"] = np.array([0, 1])
    dataset.metadata["probabilities"] = np.array([0.15])  # Wrong length

    with pytest.raises(ValueError, match="Probabilities length .* must match"):
        dataset.to_risk_assessment(outcome_code="A41.9", outcome_display="Sepsis")
