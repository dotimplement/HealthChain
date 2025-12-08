"""Tests for FHIR converters module.

Tests the converter functions that transform FHIR Bundles to DataFrames,
with focus on the dict-based conversion architecture.
"""

import pytest
import pandas as pd

from healthchain.fhir.dataframe import (
    extract_observation_value,
    group_bundle_by_patient,
    bundle_to_dataframe,
    extract_event_date,
    get_supported_resources,
    get_resource_info,
    BundleConverterConfig,
)
from healthchain.fhir import (
    create_bundle,
    add_resource,
    create_patient,
    create_value_quantity_observation,
    create_condition,
    create_medication_statement,
    prefetch_to_bundle,
)


@pytest.mark.parametrize(
    "obs_dict,expected",
    [
        ({"valueQuantity": {"value": 85.0}}, 85.0),
        ({"valueInteger": 100}, 100.0),
        ({"valueString": "98.6"}, 98.6),
        ({}, None),
        ({"valueString": "not a number"}, None),
        ({"valueBoolean": True}, None),
    ],
)
def test_extract_observation_value_handles_value_types(obs_dict, expected):
    """extract_observation_value handles different value types and invalid values."""
    assert extract_observation_value(obs_dict) == expected


def test_group_bundle_by_patient_handles_both_input_types():
    """group_bundle_by_patient handles Pydantic Bundle and dict input."""
    # Test Pydantic input
    pydantic_bundle = create_bundle()
    patient1 = create_patient("male", "1980-01-01")
    patient1.id = "123"
    add_resource(pydantic_bundle, patient1)
    add_resource(
        pydantic_bundle,
        create_value_quantity_observation(
            subject="Patient/123", code="8867-4", value=85.0, unit="bpm"
        ),
    )

    result = group_bundle_by_patient(pydantic_bundle)
    assert "Patient/123" in result
    assert isinstance(result["Patient/123"]["patient"], dict)
    assert result["Patient/123"]["patient"]["resourceType"] == "Patient"

    # Test dict input
    dict_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "456", "gender": "female"}},
            {
                "resource": {
                    "resourceType": "Observation",
                    "subject": {"reference": "Patient/456"},
                    "code": {"coding": [{"code": "8310-5"}]},
                    "valueQuantity": {"value": 37.0},
                }
            },
        ],
    }

    result = group_bundle_by_patient(dict_bundle)
    assert "Patient/456" in result
    assert len(result["Patient/456"]["observations"]) == 1


def test_group_bundle_by_patient_handles_reference_formats():
    """group_bundle_by_patient handles string and dict references, plus patient field."""
    bundle_dict = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "789"}},
            {
                "resource": {
                    "resourceType": "Observation",
                    "subject": "Patient/789",  # String reference
                    "code": {"coding": [{"code": "8867-4"}]},
                    "valueQuantity": {"value": 90.0},
                }
            },
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "patient": {"reference": "Patient/789"},  # Uses patient field
                    "code": {"coding": [{"code": "123"}]},
                }
            },
        ],
    }

    result = group_bundle_by_patient(bundle_dict)
    assert len(result["Patient/789"]["observations"]) == 1
    assert len(result["Patient/789"]["allergies"]) == 1


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

    from healthchain.fhir import (
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


def test_bundle_to_dataframe_basic_conversion():
    """bundle_to_dataframe converts both Pydantic and dict Bundles to DataFrames."""
    # Test with Pydantic Bundle
    pydantic_bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"
    add_resource(pydantic_bundle, patient)
    add_resource(
        pydantic_bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=85.0,
            unit="bpm",
            display="Heart rate",
        ),
    )

    df = bundle_to_dataframe(pydantic_bundle)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "age" in df.columns and "gender" in df.columns
    assert "8867-4_Heart_rate" in df.columns
    assert df["8867-4_Heart_rate"].iloc[0] == 85.0

    # Test with dict Bundle
    dict_bundle = {
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
                    "subject": {"reference": "Patient/456"},
                    "code": {
                        "coding": [{"code": "8310-5", "display": "Body temperature"}]
                    },
                    "valueQuantity": {"value": 37.0},
                }
            },
        ],
    }

    df = bundle_to_dataframe(dict_bundle)
    assert len(df) == 1
    assert "8310-5_Body_temperature" in df.columns


@pytest.mark.parametrize(
    "resources,source,strategy,expected",
    [
        (
            {
                "observations": [
                    {"effectiveDateTime": "2024-01-15"},
                    {"effectiveDateTime": "2024-01-10"},
                    {"effectiveDateTime": "2024-01-20"},
                ]
            },
            "Observation",
            "earliest",
            "2024-01-10",
        ),
        (
            {
                "observations": [
                    {"effectiveDateTime": "2024-01-15"},
                    {"effectiveDateTime": "2024-01-10"},
                    {"effectiveDateTime": "2024-01-20"},
                ]
            },
            "Observation",
            "latest",
            "2024-01-20",
        ),
        (
            {
                "observations": [
                    {"effectiveDateTime": "2024-01-15"},
                    {"effectiveDateTime": "2024-01-10"},
                    {"effectiveDateTime": "2024-01-20"},
                ]
            },
            "Observation",
            "first",
            "2024-01-15",
        ),
        (
            {
                "encounters": [
                    {"period": {"start": "2024-01-15T10:00:00Z"}},
                    {"period": {"start": "2024-01-10T08:00:00Z"}},
                ]
            },
            "Encounter",
            "earliest",
            "2024-01-10T08:00:00Z",
        ),
        ({}, "Observation", "earliest", None),
        ({"observations": []}, "Observation", "earliest", None),
    ],
)
def test_extract_event_date_strategies_and_sources(
    resources, source, strategy, expected
):
    """extract_event_date handles different strategies and resource sources."""
    assert extract_event_date(resources, source=source, strategy=strategy) == expected


@pytest.mark.parametrize(
    "aggregation,values,expected",
    [
        ("mean", [85.0, 92.0], 88.5),
        ("median", [85.0, 92.0, 100.0], 92.0),
        ("max", [85.0, 92.0, 100.0], 100.0),
        ("min", [85.0, 92.0, 100.0], 85.0),
        ("last", [85.0, 92.0, 100.0], 100.0),
    ],
)
def test_bundle_to_dataframe_observation_aggregation_strategies(
    aggregation, values, expected
):
    """bundle_to_dataframe applies different aggregation strategies correctly."""
    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"
    add_resource(bundle, patient)

    # Add multiple observations with same code
    for value in values:
        add_resource(
            bundle,
            create_value_quantity_observation(
                subject="Patient/123",
                code="8867-4",
                value=value,
                unit="bpm",
                display="Heart rate",
            ),
        )

    config = BundleConverterConfig(
        resources=["Patient", "Observation"], observation_aggregation=aggregation
    )
    df = bundle_to_dataframe(bundle, config=config)

    assert df["8867-4_Heart_rate"].iloc[0] == expected


def test_bundle_to_dataframe_age_calculation_modes():
    """bundle_to_dataframe calculates age from current date or event date."""
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

    # Test event_date calculation
    config = BundleConverterConfig(
        age_calculation="event_date",
        event_date_source="Observation",
        event_date_strategy="earliest",
    )
    df = bundle_to_dataframe(bundle, config=config)
    assert df["age"].iloc[0] == 40  # 2020 - 1980

    # Test current_date calculation (default)
    config_default = BundleConverterConfig()
    df_default = bundle_to_dataframe(bundle, config=config_default)
    assert df_default["age"].iloc[0] is not None


def test_bundle_to_dataframe_creates_binary_indicators_for_conditions_and_medications():
    """bundle_to_dataframe creates binary indicator columns for conditions and medications."""
    bundle = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "123"
    add_resource(bundle, patient)
    add_resource(
        bundle, create_condition("Patient/123", code="E11.9", display="Type_2_diabetes")
    )
    add_resource(
        bundle,
        create_medication_statement("Patient/123", code="1049221", display="Insulin"),
    )

    config = BundleConverterConfig(
        resources=["Patient", "Condition", "MedicationStatement"]
    )
    df = bundle_to_dataframe(bundle, config=config)

    assert "condition_E11.9_Type_2_diabetes" in df.columns
    assert df["condition_E11.9_Type_2_diabetes"].iloc[0] == 1
    assert "medication_1049221_Insulin" in df.columns
    assert df["medication_1049221_Insulin"].iloc[0] == 1


def test_bundle_to_dataframe_handles_edge_cases():
    """bundle_to_dataframe handles empty bundles and malformed data gracefully."""
    # Empty bundle
    empty_bundle = create_bundle()
    df = bundle_to_dataframe(empty_bundle)
    assert isinstance(df, pd.DataFrame) and len(df) == 0

    # Missing coding arrays - should skip bad observation
    bundle_dict = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "123",
                    "gender": "male",
                    "birthDate": "1980-01-01",
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "subject": {"reference": "Patient/123"},
                    "code": {},  # Missing coding array
                    "valueQuantity": {"value": 85.0},
                }
            },
        ],
    }

    df = bundle_to_dataframe(bundle_dict)
    assert len(df) == 1
    assert df["patient_ref"].iloc[0] == "Patient/123"

    # Missing display - should use code as fallback
    bundle_with_condition = create_bundle()
    patient = create_patient("male", "1980-01-01")
    patient.id = "456"
    add_resource(bundle_with_condition, patient)
    add_resource(bundle_with_condition, create_condition("Patient/456", code="E11.9"))

    config = BundleConverterConfig(resources=["Patient", "Condition"])
    df = bundle_to_dataframe(bundle_with_condition, config=config)
    assert "condition_E11.9_E11.9" in df.columns  # Code used as display


def test_bundle_to_dataframe_handles_multiple_patients():
    """bundle_to_dataframe creates one row per patient in multi-patient bundles."""
    bundle = create_bundle()

    # Add first patient with observations
    patient1 = create_patient("male", "1980-01-01")
    patient1.id = "123"
    add_resource(bundle, patient1)
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/123",
            code="8867-4",
            value=85.0,
            unit="bpm",
            display="Heart rate",
        ),
    )

    # Add second patient with observations
    patient2 = create_patient("female", "1990-05-15")
    patient2.id = "456"
    add_resource(bundle, patient2)
    add_resource(
        bundle,
        create_value_quantity_observation(
            subject="Patient/456",
            code="8867-4",
            value=72.0,
            unit="bpm",
            display="Heart rate",
        ),
    )

    df = bundle_to_dataframe(bundle)

    assert len(df) == 2
    assert set(df["patient_ref"]) == {"Patient/123", "Patient/456"}
    assert df[df["patient_ref"] == "Patient/123"]["8867-4_Heart_rate"].iloc[0] == 85.0
    assert df[df["patient_ref"] == "Patient/456"]["8867-4_Heart_rate"].iloc[0] == 72.0


def test_bundle_converter_config_defaults():
    """BundleConverterConfig uses sensible defaults."""
    config = BundleConverterConfig()

    assert config.resources == ["Patient", "Observation"]
    assert config.observation_aggregation == "mean"
    assert config.age_calculation == "current_date"
    assert config.event_date_source == "Observation"
    assert config.event_date_strategy == "earliest"


def test_bundle_converter_config_validates_unsupported_resources(caplog):
    """BundleConverterConfig warns about unsupported resources but doesn't fail."""
    import logging

    caplog.set_level(logging.WARNING)

    config = BundleConverterConfig(
        resources=["Patient", "Observation", "UnsupportedResource", "AnotherFakeOne"]
    )

    # Should still create config successfully
    assert "Patient" in config.resources
    assert "Observation" in config.resources

    # Should have logged warnings
    assert any("UnsupportedResource" in record.message for record in caplog.records)


def test_get_supported_resources_returns_expected_types():
    """get_supported_resources returns list of supported resource types."""
    resources = get_supported_resources()

    assert isinstance(resources, list)
    assert "Patient" in resources
    assert "Observation" in resources
    assert "Condition" in resources
    assert "MedicationStatement" in resources


def test_get_resource_info_returns_handler_details():
    """get_resource_info returns metadata for supported resources."""
    obs_info = get_resource_info("Observation")

    assert obs_info["handler"] == "_flatten_observations"
    assert "description" in obs_info
    assert "observation" in obs_info["description"].lower()

    # Unsupported resource returns empty dict
    assert get_resource_info("UnsupportedResource") == {}


def test_bundle_to_dataframe_skips_unsupported_resources_gracefully():
    """bundle_to_dataframe skips unsupported resources without error."""
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

    # Include unsupported resource types in config
    config = BundleConverterConfig(
        resources=["Patient", "Observation", "UnsupportedType"]
    )

    # Should not raise error, just skip unsupported types
    df = bundle_to_dataframe(bundle, config=config)
    assert len(df) == 1


def test_prefetch_to_bundle_flattens_cds_prefetch():
    """prefetch_to_bundle converts CDS Hooks prefetch to collection bundle."""
    prefetch = {
        "patient": {"resourceType": "Patient", "id": "123", "gender": "male"},
        "heart_rate": {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "code": {"coding": [{"code": "8867-4"}]},
                        "valueQuantity": {"value": 85.0},
                    }
                }
            ],
        },
    }

    bundle = prefetch_to_bundle(prefetch)

    assert bundle["type"] == "collection"
    assert len(bundle["entry"]) == 2
    # Patient should be wrapped in resource
    patient_entry = next(
        e
        for e in bundle["entry"]
        if e.get("resource", {}).get("resourceType") == "Patient"
    )
    assert patient_entry["resource"]["id"] == "123"


def test_prefetch_to_bundle_handles_empty_prefetch():
    """prefetch_to_bundle handles empty prefetch gracefully."""
    bundle = prefetch_to_bundle({})
    assert bundle["type"] == "collection"
    assert bundle["entry"] == []
