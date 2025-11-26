"""Tests for FHIR converters module.

Tests the converter functions that transform FHIR Bundles to DataFrames,
with focus on the dict-based conversion architecture.
"""

# TODO: check test coverage
import pandas as pd


from healthchain.fhir.converters import (
    extract_observation_value,
    group_bundle_by_patient,
    bundle_to_dataframe,
)
from healthchain.fhir import create_bundle, add_resource
from healthchain.fhir.helpers import create_patient, create_value_quantity_observation


def test_extract_observation_value_from_quantity():
    """extract_observation_value handles valueQuantity."""
    obs_dict = {
        "valueQuantity": {
            "value": 85.0,
            "unit": "beats/min",
            "system": "http://unitsofmeasure.org",
        }
    }
    assert extract_observation_value(obs_dict) == 85.0


def test_extract_observation_value_from_string():
    """extract_observation_value handles valueString."""
    obs_dict = {"valueString": "98.6"}
    assert extract_observation_value(obs_dict) == 98.6


def test_extract_observation_value_returns_none_for_invalid():
    """extract_observation_value returns None for non-numeric or missing values."""
    assert extract_observation_value({}) is None
    assert extract_observation_value({"valueString": "not a number"}) is None
    assert extract_observation_value({"valueBoolean": True}) is None


def test_group_bundle_by_patient_converts_pydantic_to_dict():
    """group_bundle_by_patient converts Pydantic Bundle to dict internally."""
    # Create Pydantic bundle
    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"

    add_resource(bundle, patient)
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123", code="8867-4", value=85.0, unit="bpm"
        ),
    )

    # Should handle Pydantic input
    result = group_bundle_by_patient(bundle)

    assert "Patient/123" in result
    assert result["Patient/123"]["patient"] is not None
    assert len(result["Patient/123"]["observations"]) == 1

    # Result should contain dicts, not Pydantic objects
    patient_resource = result["Patient/123"]["patient"]
    assert isinstance(patient_resource, dict)
    assert patient_resource["resourceType"] == "Patient"


def test_group_bundle_by_patient_handles_dict_bundle():
    """group_bundle_by_patient works with dict input (no conversion needed)."""
    bundle_dict = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "456",
                    "gender": "female",
                    "birthDate": "1990-05-15",
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-1",
                    "subject": {"reference": "Patient/456"},
                    "code": {"coding": [{"code": "8310-5"}]},
                    "valueQuantity": {"value": 37.0},
                }
            },
        ],
    }

    result = group_bundle_by_patient(bundle_dict)

    assert "Patient/456" in result
    assert result["Patient/456"]["patient"]["id"] == "456"
    assert len(result["Patient/456"]["observations"]) == 1


def test_group_bundle_by_patient_handles_string_references():
    """group_bundle_by_patient handles subject fields that are strings."""
    bundle_dict = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "789"}},
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-2",
                    "subject": "Patient/789",  # String, not dict!
                    "code": {"coding": [{"code": "8867-4"}]},
                    "valueQuantity": {"value": 90.0},
                }
            },
        ],
    }

    result = group_bundle_by_patient(bundle_dict)

    assert "Patient/789" in result
    assert len(result["Patient/789"]["observations"]) == 1


def test_group_bundle_by_patient_handles_patient_field():
    """group_bundle_by_patient uses 'patient' field for AllergyIntolerance."""
    bundle_dict = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "111"}},
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": "allergy-1",
                    "patient": {"reference": "Patient/111"},
                    "code": {"coding": [{"code": "123"}]},
                }
            },
        ],
    }

    result = group_bundle_by_patient(bundle_dict)

    assert "Patient/111" in result
    assert len(result["Patient/111"]["allergies"]) == 1


def test_group_bundle_by_patient_groups_multiple_resource_types():
    """group_bundle_by_patient correctly categorizes different resource types."""
    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "999"

    add_resource(bundle, patient)

    # Add one of each type
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/999", code="8867-4", value=85.0, unit="bpm"
        ),
    )

    from healthchain.fhir.helpers import (
        create_condition,
        create_medication_statement,
        create_allergy_intolerance,
    )

    add_resource(bundle, create_condition("Patient/999", code="E11.9"))
    add_resource(bundle, create_medication_statement("Patient/999", code="123"))
    add_resource(bundle, create_allergy_intolerance("Patient/999", code="456"))

    result = group_bundle_by_patient(bundle)

    assert len(result["Patient/999"]["observations"]) == 1
    assert len(result["Patient/999"]["conditions"]) == 1
    assert len(result["Patient/999"]["medications"]) == 1
    assert len(result["Patient/999"]["allergies"]) == 1


def test_bundle_to_dataframe_with_pydantic_bundle():
    """bundle_to_dataframe handles Pydantic Bundle input."""
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

    df = bundle_to_dataframe(bundle)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "patient_ref" in df.columns
    assert df["patient_ref"].iloc[0] == "Patient/123"
    assert "age" in df.columns
    assert "gender" in df.columns
    assert "8867-4_Heart_rate" in df.columns
    assert df["8867-4_Heart_rate"].iloc[0] == 85.0


def test_bundle_to_dataframe_with_dict_bundle():
    """bundle_to_dataframe handles dict Bundle input."""
    bundle_dict = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "456",
                    "gender": "female",
                    "birthDate": "1990-05-15",
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-1",
                    "subject": {"reference": "Patient/456"},
                    "code": {
                        "coding": [
                            {
                                "code": "8310-5",
                                "display": "Body temperature",
                                "system": "http://loinc.org",
                            }
                        ]
                    },
                    "valueQuantity": {"value": 37.0},
                }
            },
        ],
    }

    df = bundle_to_dataframe(bundle_dict)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df["patient_ref"].iloc[0] == "Patient/456"
    assert "8310-5_Body_temperature" in df.columns
