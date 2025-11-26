import pytest
import pandas as pd
from pathlib import Path

from healthchain.io.containers.featureschema import FeatureSchema
from healthchain.io.containers.dataset import Dataset
from healthchain.fhir import create_bundle
from healthchain.fhir import create_patient, create_value_quantity_observation


@pytest.fixture
def sepsis_schema():
    """Load the actual sepsis_vitals.yaml schema.

    Uses the real schema file for integration-style testing.
    """
    schema_path = Path("healthchain/configs/features/sepsis_vitals.yaml")
    return FeatureSchema.from_yaml(schema_path)


@pytest.fixture
def minimal_schema():
    """Minimal schema with required and optional features.

    Useful for testing basic functionality without all the complexity
    of the full sepsis schema.
    """
    return FeatureSchema.from_dict(
        {
            "name": "test_schema",
            "version": "1.0",
            "features": {
                "heart_rate": {
                    "fhir_resource": "Observation",
                    "code": "8867-4",
                    "code_system": "http://loinc.org",
                    "display": "Heart rate",
                    "dtype": "float64",
                    "required": True,
                },
                "temperature": {
                    "fhir_resource": "Observation",
                    "code": "8310-5",
                    "code_system": "http://loinc.org",
                    "display": "Body temperature",
                    "dtype": "float64",
                    "required": False,
                },
                "age": {
                    "fhir_resource": "Patient",
                    "field": "birthDate",
                    "transform": "calculate_age",
                    "dtype": "int64",
                    "required": True,
                },
                "gender_encoded": {
                    "fhir_resource": "Patient",
                    "field": "gender",
                    "transform": "encode_gender",
                    "dtype": "int64",
                    "required": True,
                },
            },
        }
    )


@pytest.fixture
def observation_bundle():
    """Bundle with patient and observations matching minimal schema.

    Contains a single patient with heart rate and temperature observations.
    """
    from healthchain.fhir import add_resource

    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"

    # Use add_resource to properly add to bundle
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
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8310-5",
            value=37.0,
            unit="F",
            system="http://loinc.org",
            display="Body temperature",
        ),
    )

    return bundle


@pytest.fixture
def observation_bundle_with_duplicates():
    """Bundle with multiple observations of the same type for testing aggregation."""
    from healthchain.fhir import add_resource

    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"

    # Use add_resource consistently like observation_bundle
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
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=90.0,
            unit="bpm",
            system="http://loinc.org",
            display="Heart rate",
        ),
    )
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=88.0,
            unit="bpm",
            system="http://loinc.org",
            display="Heart rate",
        ),
    )

    return bundle


@pytest.fixture
def empty_observation_bundle():
    """Bundle with patient but no observations."""
    from healthchain.fhir import add_resource

    bundle = create_bundle()
    patient = create_patient("female", "1990-05-15")
    patient.id = "456"

    add_resource(bundle, patient)
    return bundle


@pytest.fixture
def sample_dataset():
    """Sample dataset with minimal schema features.

    Contains two patients with complete feature data.
    """
    data = {
        "patient_ref": ["Patient/1", "Patient/2"],
        "heart_rate": [85.0, 92.0],
        "temperature": [37.0, 37.5],
        "age": [45, 62],
        "gender_encoded": [1, 0],
    }
    return Dataset(pd.DataFrame(data))


@pytest.fixture
def sample_dataset_incomplete():
    """Sample dataset missing required features.

    Useful for testing validation logic.
    """
    data = {
        "patient_ref": ["Patient/1", "Patient/2"],
        "heart_rate": [85.0, 92.0],
        # Missing temperature (optional), age, and gender_encoded (required)
    }
    return Dataset(pd.DataFrame(data))


@pytest.fixture
def sample_dataset_wrong_types():
    """Sample dataset with incorrect data types.

    Useful for testing type validation logic.
    """
    data = {
        "patient_ref": ["Patient/1", "Patient/2"],
        "heart_rate": ["85.0", "92.0"],  # String instead of float
        "temperature": [37.0, 37.5],
        "age": [45.5, 62.5],  # Float instead of int
        "gender_encoded": [1, 0],
    }
    return Dataset(pd.DataFrame(data))
