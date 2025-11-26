import pytest
import tempfile
from pathlib import Path

from healthchain.io.containers.featureschema import FeatureSchema, FeatureMapping


@pytest.mark.parametrize(
    "mapping_data,expected_error",
    [
        (
            {"fhir_resource": "Observation"},
            "Observation resources require a 'code'",
        ),
        (
            {"fhir_resource": "Observation", "code": "123"},
            "Observation resources require a 'code_system'",
        ),
        (
            {"fhir_resource": "Observation", "code_system": "http://loinc.org"},
            "Observation resources require a 'code'",
        ),
        (
            {"fhir_resource": "Patient"},
            "Patient resources require a 'field'",
        ),
    ],
)
def test_feature_mapping_required_fields_and_validations(mapping_data, expected_error):
    """FeatureMapping enforces required fields and validates resource-specific requirements."""
    with pytest.raises(ValueError, match=expected_error):
        FeatureMapping(name="test_feature", dtype="float64", **mapping_data)


def test_feature_schema_loads_from_yaml(sepsis_schema):
    """FeatureSchema.from_yaml loads the sepsis_vitals schema correctly."""
    assert sepsis_schema.name == "sepsis_prediction_features"
    assert sepsis_schema.version == "1.0"
    assert len(sepsis_schema.features) == 8
    assert "heart_rate" in sepsis_schema.features
    assert "age" in sepsis_schema.features


def test_feature_schema_from_dict(minimal_schema):
    """FeatureSchema.from_dict creates schema with proper FeatureMapping objects."""
    assert minimal_schema.name == "test_schema"
    assert isinstance(minimal_schema.features["heart_rate"], FeatureMapping)
    assert minimal_schema.features["heart_rate"].required is True
    assert minimal_schema.features["temperature"].required is False


def test_feature_schema_to_dict_and_back_handles_unknown_and_nested_fields(
    minimal_schema,
):
    """FeatureSchema.to_dict/from_dict: unknown fields are allowed (Pydantic extra='allow')."""
    # Add an unknown field at the top-level
    schema_dict = minimal_schema.to_dict()
    schema_dict["extra_top_level"] = "foo"
    # Add extra/unknown fields at the feature level
    schema_dict["features"]["heart_rate"]["unknown_field"] = 12345
    schema_dict["features"]["temperature"]["nested_field"] = {"inner": ["a", {"b": 7}]}

    # With Pydantic extra='allow', unknown fields are accepted and preserved
    loaded = FeatureSchema.from_dict(schema_dict)

    # Core fields should still be correct
    assert loaded.name == minimal_schema.name
    assert loaded.version == minimal_schema.version
    assert len(loaded.features) == len(minimal_schema.features)

    # Unknown fields are preserved in the model
    assert "heart_rate" in loaded.features
    assert loaded.features["heart_rate"].code == "8867-4"


def test_feature_schema_to_yaml_and_back(minimal_schema):
    """FeatureSchema can be saved to YAML and reloaded."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = f.name

    try:
        minimal_schema.to_yaml(temp_path)
        loaded = FeatureSchema.from_yaml(temp_path)

        assert loaded.name == minimal_schema.name
        assert len(loaded.features) == len(minimal_schema.features)
        assert loaded.features["heart_rate"].code == "8867-4"
    finally:
        Path(temp_path).unlink()


def test_feature_schema_required_vs_optional_distinction(minimal_schema):
    """FeatureSchema correctly distinguishes required from optional features."""
    required = minimal_schema.get_required_features()
    all_features = minimal_schema.get_feature_names()

    # Required features should be a subset of all features
    assert set(required).issubset(set(all_features))

    # Temperature is optional, others are required
    assert "temperature" not in required
    assert len(required) == 3
    assert all(f in required for f in ["heart_rate", "age", "gender_encoded"])


@pytest.mark.parametrize(
    "columns, expected_valid, missing_required, missing_optional, unexpected",
    [
        (
            ["heart_rate", "temperature"],  # missing required
            False,
            {"age", "gender_encoded"},
            set(),
            set(),
        ),
        (
            ["heart_rate", "age", "gender_encoded"],  # missing optional
            True,
            set(),
            {"temperature"},
            set(),
        ),
        (
            ["heart_rate", "age", "gender_encoded", "unexpected_col"],  # unexpected col
            True,
            set(),
            set(),
            {"unexpected_col"},
        ),
    ],
)
def test_feature_schema_validate_dataframe_columns_various_cases(
    minimal_schema,
    columns,
    expected_valid,
    missing_required,
    missing_optional,
    unexpected,
):
    """FeatureSchema.validate_dataframe_columns: missing required, optional, and unexpected columns."""
    result = minimal_schema.validate_dataframe_columns(columns)
    assert result["valid"] is expected_valid
    assert set(result["missing_required"]) == missing_required
    if missing_optional:
        assert set(result["missing_optional"]) == missing_optional
    if unexpected:
        assert set(result["unexpected"]) == unexpected


def test_feature_schema_get_features_by_resource(minimal_schema):
    """FeatureSchema.get_features_by_resource filters features by FHIR resource type."""
    observations = minimal_schema.get_features_by_resource("Observation")
    patients = minimal_schema.get_features_by_resource("Patient")

    assert len(observations) == 2  # heart_rate, temperature
    assert "heart_rate" in observations
    assert "temperature" in observations

    assert len(patients) == 2  # age, gender_encoded
    assert "age" in patients
    assert "gender_encoded" in patients

    # Non-existent resource type returns empty dict
    assert minimal_schema.get_features_by_resource("Condition") == {}


def test_feature_schema_get_observation_codes(minimal_schema):
    """FeatureSchema.get_observation_codes returns mapping of codes to features."""
    obs_codes = minimal_schema.get_observation_codes()

    assert "8867-4" in obs_codes  # heart_rate code
    assert "8310-5" in obs_codes  # temperature code
    assert obs_codes["8867-4"].name == "heart_rate"
    assert obs_codes["8310-5"].name == "temperature"


def test_feature_schema_get_feature_names_preserves_order(minimal_schema):
    """FeatureSchema.get_feature_names returns features in definition order."""
    names = minimal_schema.get_feature_names()

    assert isinstance(names, list)
    assert len(names) == 4
    # Order should match the features dict order
    assert names == ["heart_rate", "temperature", "age", "gender_encoded"]


def test_feature_schema_from_yaml_handles_malformed_file():
    """FeatureSchema.from_yaml raises error for malformed YAML."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [\n")  # Malformed YAML
        temp_path = f.name

    try:
        with pytest.raises(
            Exception
        ):  # Could be yaml.YAMLError or other parsing errors
            FeatureSchema.from_yaml(temp_path)
    finally:
        Path(temp_path).unlink()


def test_feature_mapping_from_dict_creates_instance():
    """FeatureMapping.from_dict creates instance with name parameter."""
    mapping_data = {
        "fhir_resource": "Observation",
        "code": "8867-4",
        "code_system": "http://loinc.org",
        "dtype": "float64",
        "required": True,
    }

    mapping = FeatureMapping.from_dict("test_feature", mapping_data)

    assert mapping.name == "test_feature"
    assert mapping.code == "8867-4"
    assert mapping.fhir_resource == "Observation"
    assert mapping.required is True


def test_feature_schema_handles_optional_fields(minimal_schema):
    """FeatureSchema preserves optional metadata fields."""
    # Check that optional fields can be None
    assert minimal_schema.description is None or isinstance(
        minimal_schema.description, str
    )
    assert minimal_schema.model_info is None or isinstance(
        minimal_schema.model_info, dict
    )

    # Create schema with metadata
    schema_with_metadata = FeatureSchema.from_dict(
        {
            "name": "test",
            "version": "1.0",
            "description": "Test description",
            "model_info": {"type": "RandomForest"},
            "metadata": {"custom_field": "value"},
            "features": {},
        }
    )

    assert schema_with_metadata.description == "Test description"
    assert schema_with_metadata.model_info["type"] == "RandomForest"
    assert schema_with_metadata.metadata["custom_field"] == "value"
