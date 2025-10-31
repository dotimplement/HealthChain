"""Tests for Synthea FHIR Patient dataset loader."""

import json
import tempfile
from pathlib import Path

import pytest

from healthchain.sandbox.loaders.synthea import SyntheaFHIRPatientLoader


@pytest.fixture
def temp_synthea_data_dir():
    """Create temporary Synthea data directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_patient_bundle():
    """Sample Synthea patient Bundle with multiple resource types."""
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "a969c177-a995-7b89-7b6d-885214dfa253",
                    "name": [{"given": ["Alton"], "family": "Gutkowski"}],
                    "gender": "male",
                    "birthDate": "1980-01-01",
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-1",
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "active",
                            }
                        ]
                    },
                    "code": {
                        "coding": [
                            {"system": "http://snomed.info/sct", "code": "44054006"}
                        ]
                    },
                    "subject": {
                        "reference": "Patient/a969c177-a995-7b89-7b6d-885214dfa253"
                    },
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-2",
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "active",
                            }
                        ]
                    },
                    "code": {
                        "coding": [
                            {"system": "http://snomed.info/sct", "code": "38341003"}
                        ]
                    },
                    "subject": {
                        "reference": "Patient/a969c177-a995-7b89-7b6d-885214dfa253"
                    },
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationStatement",
                    "id": "med-1",
                    "status": "recorded",
                    "medication": {
                        "concept": {
                            "coding": [
                                {
                                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                    "code": "313782",
                                }
                            ]
                        }
                    },
                    "subject": {
                        "reference": "Patient/a969c177-a995-7b89-7b6d-885214dfa253"
                    },
                }
            },
        ],
    }


def create_patient_file(data_dir: Path, filename: str, bundle: dict) -> Path:
    """Helper to create patient Bundle JSON file."""
    file_path = data_dir / filename
    with open(file_path, "w") as f:
        json.dump(bundle, f)
    return file_path


@pytest.mark.parametrize(
    "patient_spec,filename",
    [
        (
            {"patient_id": "a969c177-a995-7b89-7b6d-885214dfa253"},
            "Alton320_Gutkowski940_a969c177-a995-7b89-7b6d-885214dfa253.json",
        ),
        (
            {
                "patient_file": "Alton320_Gutkowski940_a969c177-a995-7b89-7b6d-885214dfa253.json"
            },
            "Alton320_Gutkowski940_a969c177-a995-7b89-7b6d-885214dfa253.json",
        ),
        ({}, "Patient1.json"),  # Default: first file
    ],
)
def test_synthea_loader_supports_multiple_file_specification_methods(
    temp_synthea_data_dir, mock_patient_bundle, patient_spec, filename
):
    """SyntheaFHIRPatientLoader supports patient_id, patient_file, and default loading."""
    create_patient_file(temp_synthea_data_dir, filename, mock_patient_bundle)

    loader = SyntheaFHIRPatientLoader()
    result = loader.load(data_dir=str(temp_synthea_data_dir), **patient_spec)

    assert isinstance(result, dict)
    assert "patient" in result and "condition" in result
    # Returns Bundle objects
    assert type(result["patient"]).__name__ == "Bundle"
    assert len(result["patient"].entry) == 1
    assert len(result["condition"].entry) == 2


def test_synthea_loader_filters_and_groups_resources_by_type(
    temp_synthea_data_dir, mock_patient_bundle
):
    """SyntheaFHIRPatientLoader filters by resource_types and groups into separate Bundles."""
    filename = "Patient1.json"
    create_patient_file(temp_synthea_data_dir, filename, mock_patient_bundle)

    loader = SyntheaFHIRPatientLoader()
    result = loader.load(
        data_dir=str(temp_synthea_data_dir),
        resource_types=["Condition", "MedicationStatement"],
    )

    # Only requested types included
    assert set(result.keys()) == {"condition", "medicationstatement"}
    assert len(result["condition"].entry) == 2
    assert len(result["medicationstatement"].entry) == 1


@pytest.mark.parametrize("sample_size,expected_count", [(1, 1), (2, 2)])
def test_synthea_loader_sampling_behavior(
    temp_synthea_data_dir, mock_patient_bundle, sample_size, expected_count
):
    """SyntheaFHIRPatientLoader samples specified number of resources per type."""
    create_patient_file(temp_synthea_data_dir, "Patient1.json", mock_patient_bundle)

    loader = SyntheaFHIRPatientLoader()
    result = loader.load(
        data_dir=str(temp_synthea_data_dir),
        resource_types=["Condition"],
        sample_size=sample_size,
    )

    assert len(result["condition"].entry) == expected_count


def test_synthea_loader_deterministic_sampling_with_seed(
    temp_synthea_data_dir, mock_patient_bundle
):
    """SyntheaFHIRPatientLoader produces consistent results with random_seed."""
    create_patient_file(temp_synthea_data_dir, "Patient1.json", mock_patient_bundle)

    loader = SyntheaFHIRPatientLoader()
    result1 = loader.load(
        data_dir=str(temp_synthea_data_dir),
        resource_types=["Condition"],
        sample_size=1,
        random_seed=42,
    )
    result2 = loader.load(
        data_dir=str(temp_synthea_data_dir),
        resource_types=["Condition"],
        sample_size=1,
        random_seed=42,
    )

    assert (
        result1["condition"].entry[0].resource.id
        == result2["condition"].entry[0].resource.id
    )


@pytest.mark.parametrize(
    "error_case,error_match",
    [
        ({"data_dir": "/nonexistent"}, "Synthea data directory not found"),
        ({"patient_id": "nonexistent-uuid"}, "No patient file found with ID"),
        ({"patient_file": "nonexistent.json"}, "Patient file not found"),
    ],
)
def test_synthea_loader_error_handling_for_missing_files(
    temp_synthea_data_dir, mock_patient_bundle, error_case, error_match
):
    """SyntheaFHIRPatientLoader raises clear errors for missing files and directories."""
    if "data_dir" not in error_case:
        error_case["data_dir"] = str(temp_synthea_data_dir)

    loader = SyntheaFHIRPatientLoader()
    with pytest.raises(FileNotFoundError, match=error_match):
        loader.load(**error_case)


def test_synthea_loader_raises_error_for_multiple_matching_patient_ids(
    temp_synthea_data_dir, mock_patient_bundle
):
    """SyntheaFHIRPatientLoader raises ValueError when patient_id matches multiple files."""
    create_patient_file(
        temp_synthea_data_dir, "Patient1_a969c177.json", mock_patient_bundle
    )
    create_patient_file(
        temp_synthea_data_dir, "Patient2_a969c177.json", mock_patient_bundle
    )

    loader = SyntheaFHIRPatientLoader()
    with pytest.raises(ValueError, match="Multiple patient files found"):
        loader.load(data_dir=str(temp_synthea_data_dir), patient_id="a969c177")


@pytest.mark.parametrize(
    "invalid_bundle,error_match",
    [
        ({"not": "a bundle"}, "is not a FHIR Bundle"),
        ({"resourceType": "Patient"}, "is not a FHIR Bundle"),
        ({"resourceType": "Bundle"}, "has no 'entry' field"),
    ],
)
def test_synthea_loader_validates_bundle_structure(
    temp_synthea_data_dir, invalid_bundle, error_match
):
    """SyntheaFHIRPatientLoader validates Bundle structure and raises errors for invalid data."""
    create_patient_file(temp_synthea_data_dir, "Invalid.json", invalid_bundle)

    loader = SyntheaFHIRPatientLoader()
    with pytest.raises(ValueError, match=error_match):
        loader.load(data_dir=str(temp_synthea_data_dir))


def test_synthea_loader_raises_error_for_nonexistent_resource_types(
    temp_synthea_data_dir, mock_patient_bundle
):
    """SyntheaFHIRPatientLoader raises error when requested resource_types don't exist."""
    create_patient_file(temp_synthea_data_dir, "Patient1.json", mock_patient_bundle)

    loader = SyntheaFHIRPatientLoader()
    with pytest.raises(ValueError, match="No resources found for requested types"):
        loader.load(
            data_dir=str(temp_synthea_data_dir),
            resource_types=["Observation", "Procedure"],  # Not in bundle
        )


def test_synthea_loader_skips_resources_without_resource_type(temp_synthea_data_dir):
    """SyntheaFHIRPatientLoader skips entries missing resourceType field."""
    invalid_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"id": "no-type"}},  # Missing resourceType
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-1",
                    "gender": "male",
                    "birthDate": "1980-01-01",
                }
            },
        ],
    }
    create_patient_file(temp_synthea_data_dir, "Patient1.json", invalid_bundle)

    loader = SyntheaFHIRPatientLoader()
    result = loader.load(data_dir=str(temp_synthea_data_dir))

    # Should only load valid Patient resource
    assert "patient" in result
    assert len(result["patient"].entry) == 1
