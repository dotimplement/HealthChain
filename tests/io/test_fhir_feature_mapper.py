import pytest
import numpy as np

from healthchain.io.mappers.fhirfeaturemapper import FHIRFeatureMapper


def test_mapper_extracts_features_from_bundle(observation_bundle, minimal_schema):
    """FHIRFeatureMapper extracts features matching schema from FHIR Bundle."""
    mapper = FHIRFeatureMapper(minimal_schema)
    df = mapper.extract_features(observation_bundle)

    assert len(df) == 1
    assert "patient_ref" in df.columns
    assert df["patient_ref"].iloc[0] == "Patient/123"
    assert "heart_rate" in df.columns
    assert "temperature" in df.columns
    assert "age" in df.columns
    assert "gender_encoded" in df.columns


@pytest.mark.parametrize(
    "aggregation,expected_value",
    [
        ("mean", 87.666667),
        ("median", 88.0),
        ("max", 90.0),
        ("min", 85.0),
        ("last", 88.0),
    ],
)
def test_mapper_aggregation_methods(
    observation_bundle_with_duplicates, minimal_schema, aggregation, expected_value
):
    """FHIRFeatureMapper correctly aggregates multiple observation values."""
    mapper = FHIRFeatureMapper(minimal_schema)
    df = mapper.extract_features(
        observation_bundle_with_duplicates, aggregation=aggregation
    )

    assert len(df) == 1
    assert df["heart_rate"].iloc[0] == pytest.approx(expected_value, rel=1e-5)


def test_mapper_fills_missing_observations_with_nan(
    empty_observation_bundle, minimal_schema
):
    """FHIRFeatureMapper fills missing observations with NaN."""
    mapper = FHIRFeatureMapper(minimal_schema)
    df = mapper.extract_features(empty_observation_bundle)

    assert len(df) == 1
    assert df["patient_ref"].iloc[0] == "Patient/456"
    # Patient features should be present
    assert df["age"].notna().iloc[0]
    assert df["gender_encoded"].notna().iloc[0]
    # Observation features should be NaN
    assert np.isnan(df["heart_rate"].iloc[0])
    assert np.isnan(df["temperature"].iloc[0])


def test_mapper_column_mapping_from_generic_to_schema():
    """FHIRFeatureMapper correctly maps generic column names to schema feature names."""
    from healthchain.fhir import (
        create_bundle,
        add_resource,
        create_patient,
        create_value_quantity_observation,
    )
    from healthchain.io.containers.featureschema import FeatureSchema

    # Create schema with specific LOINC codes
    schema = FeatureSchema.from_dict(
        {
            "name": "test_schema",
            "version": "1.0",
            "features": {
                "hr": {  # Schema uses "hr" as feature name
                    "fhir_resource": "Observation",
                    "code": "8867-4",  # LOINC for heart rate
                    "code_system": "http://loinc.org",
                    "dtype": "float64",
                    "required": True,
                }
            },
        }
    )

    # Create bundle with observation that has code 8867-4
    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"
    add_resource(bundle, patient)
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=85.0,
            unit="bpm",
            system="http://loinc.org",
            display="Heart rate",
        ),
    )

    mapper = FHIRFeatureMapper(schema)
    df = mapper.extract_features(bundle)

    # Should be renamed to "hr" not "8867-4_Heart_rate"
    assert "hr" in df.columns
    assert df["hr"].iloc[0] == 85.0


def test_mapper_handles_bundle_with_no_matching_observations(observation_bundle):
    """FHIRFeatureMapper handles bundle with observations that don't match schema."""
    from healthchain.io.containers.featureschema import FeatureSchema

    # Schema with different codes than what's in the bundle
    schema = FeatureSchema.from_dict(
        {
            "name": "test_schema",
            "version": "1.0",
            "features": {
                "blood_pressure": {
                    "fhir_resource": "Observation",
                    "code": "85354-9",  # Different code
                    "code_system": "http://loinc.org",
                    "dtype": "float64",
                    "required": False,
                }
            },
        }
    )

    mapper = FHIRFeatureMapper(schema)
    df = mapper.extract_features(observation_bundle)

    assert len(df) == 1
    assert "blood_pressure" in df.columns
    assert np.isnan(df["blood_pressure"].iloc[0])


def test_mapper_extracts_patient_demographics(observation_bundle, minimal_schema):
    """FHIRFeatureMapper correctly extracts and transforms patient demographics."""
    mapper = FHIRFeatureMapper(minimal_schema)
    df = mapper.extract_features(observation_bundle)

    # Age should be calculated from birthDate (1980-01-01)
    assert df["age"].iloc[0] > 40  # Age should be around 44-45
    assert df["age"].dtype == np.int64

    # Gender should be encoded (male = 1)
    assert df["gender_encoded"].iloc[0] == 1
    assert df["gender_encoded"].dtype == np.int64


def test_mapper_preserves_column_order_from_schema(observation_bundle, minimal_schema):
    """FHIRFeatureMapper returns DataFrame with columns ordered as in schema."""
    mapper = FHIRFeatureMapper(minimal_schema)
    df = mapper.extract_features(observation_bundle)

    expected_order = ["patient_ref"] + minimal_schema.get_feature_names()
    assert list(df.columns) == expected_order


def test_mapper_handles_multiple_patients():
    """FHIRFeatureMapper processes multiple patients in a bundle."""
    from healthchain.fhir import (
        create_bundle,
        add_resource,
        create_patient,
        create_value_quantity_observation,
    )
    from healthchain.io.containers.featureschema import FeatureSchema

    schema = FeatureSchema.from_dict(
        {
            "name": "test_schema",
            "version": "1.0",
            "features": {
                "heart_rate": {
                    "fhir_resource": "Observation",
                    "code": "8867-4",
                    "code_system": "http://loinc.org",
                    "dtype": "float64",
                    "required": True,
                }
            },
        }
    )

    bundle = create_bundle()
    patient1 = create_patient("male", "1980-01-01")
    patient1.id = "123"
    patient2 = create_patient("female", "1990-05-15")
    patient2.id = "456"

    add_resource(bundle, patient1)
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=85.0,
            unit="bpm",
            system="http://loinc.org",
        ),
    )
    add_resource(bundle, patient2)
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/456",
            code="8867-4",
            value=92.0,
            unit="bpm",
            system="http://loinc.org",
        ),
    )

    mapper = FHIRFeatureMapper(schema)
    df = mapper.extract_features(bundle)

    assert len(df) == 2
    assert set(df["patient_ref"]) == {"Patient/123", "Patient/456"}
    assert 85.0 in df["heart_rate"].values
    assert 92.0 in df["heart_rate"].values


def test_mapper_aggregation_with_mixed_values():
    """FHIRFeatureMapper aggregates correctly with extreme value differences."""
    from healthchain.fhir import (
        create_bundle,
        add_resource,
        create_patient,
        create_value_quantity_observation,
    )
    from healthchain.io.containers.featureschema import FeatureSchema

    schema = FeatureSchema.from_dict(
        {
            "name": "test_schema",
            "version": "1.0",
            "features": {
                "heart_rate": {
                    "fhir_resource": "Observation",
                    "code": "8867-4",
                    "code_system": "http://loinc.org",
                    "dtype": "float64",
                    "required": True,
                }
            },
        }
    )

    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"

    # Extreme values
    add_resource(bundle, patient)
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=50.0,
            unit="bpm",
            system="http://loinc.org",
        ),
    )
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=100.0,
            unit="bpm",
            system="http://loinc.org",
        ),
    )
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=75.0,
            unit="bpm",
            system="http://loinc.org",
        ),
    )

    mapper = FHIRFeatureMapper(schema)

    # Test different aggregation methods
    df_mean = mapper.extract_features(bundle, aggregation="mean")
    assert df_mean["heart_rate"].iloc[0] == 75.0

    df_max = mapper.extract_features(bundle, aggregation="max")
    assert df_max["heart_rate"].iloc[0] == 100.0

    df_min = mapper.extract_features(bundle, aggregation="min")
    assert df_min["heart_rate"].iloc[0] == 50.0


def test_mapper_with_schema_metadata_configuration():
    """FHIRFeatureMapper uses schema metadata for age calculation."""
    from healthchain.fhir import (
        create_bundle,
        add_resource,
        create_patient,
        create_value_quantity_observation,
    )
    from healthchain.io.containers.featureschema import FeatureSchema

    schema = FeatureSchema.from_dict(
        {
            "name": "test_schema",
            "version": "1.0",
            "metadata": {
                "age_calculation": "event_date",
                "event_date_source": "Observation",
                "event_date_strategy": "earliest",
            },
            "features": {
                "heart_rate": {
                    "fhir_resource": "Observation",
                    "code": "8867-4",
                    "code_system": "http://loinc.org",
                    "dtype": "float64",
                    "required": True,
                },
                "age": {
                    "fhir_resource": "Patient",
                    "field": "birthDate",
                    "transform": "calculate_age",
                    "dtype": "int64",
                    "required": True,
                },
            },
        }
    )

    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"

    add_resource(bundle, patient)
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=85.0,
            unit="bpm",
            effective_datetime="2020-01-01T00:00:00Z",
        ),
    )

    mapper = FHIRFeatureMapper(schema)
    df = mapper.extract_features(bundle)

    # Age should be calculated from birthdate to event date (40 years)
    assert df["age"].iloc[0] == 40
