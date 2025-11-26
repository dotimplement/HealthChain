import pytest
import tempfile
from pathlib import Path

from healthchain.io.containers.featureschema import FeatureSchema, FeatureMapping


# TODO: Complete test coverage
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
    """FeatureSchema.to_dict/from_dict: unknown feature-level fields raise TypeError, unknown top-level fields are ignored."""
    # Add an unknown field at the top-level (should be ignored)
    schema_dict = minimal_schema.to_dict()
    schema_dict["extra_top_level"] = "foo"
    # Add extra/unknown fields at the feature level (should raise TypeError on from_dict)
    schema_dict["features"]["heart_rate"]["unknown_field"] = 12345
    schema_dict["features"]["temperature"]["nested_field"] = {"inner": ["a", {"b": 7}]}

    # Top-level unknown fields are ignored by FeatureSchema dataclass
    # But unknown fields within "features" will cause a TypeError in FeatureMapping.__init__
    with pytest.raises(TypeError) as excinfo:
        FeatureSchema.from_dict(schema_dict)
    # The error message will refer to the first unknown field encountered, either "unknown_field" or "nested_field"
    assert "unexpected keyword argument" in str(excinfo.value)


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
