"""Tests for MIMIC-on-FHIR dataset loader."""

import gzip
import json
import tempfile
from pathlib import Path

import pytest

from healthchain.sandbox.loaders.mimic import MimicOnFHIRLoader


@pytest.fixture
def temp_mimic_data_dir():
    """Create temporary MIMIC-on-FHIR data directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = Path(tmpdir)
        fhir_dir = data_path / "fhir"
        fhir_dir.mkdir()
        yield data_path


@pytest.fixture
def mock_medication_resources():
    """Sample MedicationStatement resources for testing."""
    return [
        {
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
            "subject": {"reference": "Patient/123"},
        },
        {
            "resourceType": "MedicationStatement",
            "id": "med-2",
            "status": "recorded",
            "medication": {
                "concept": {
                    "coding": [
                        {
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": "197361",
                        }
                    ]
                }
            },
            "subject": {"reference": "Patient/456"},
        },
    ]


@pytest.fixture
def mock_condition_resources():
    """Sample Condition resources for testing."""
    return [
        {
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
                "coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]
            },
            "subject": {"reference": "Patient/123"},
        }
    ]


def create_ndjson_gz_file(file_path: Path, resources: list):
    """Helper to create gzipped NDJSON file."""
    with gzip.open(file_path, "wt") as f:
        for resource in resources:
            f.write(json.dumps(resource) + "\n")


def test_mimic_loader_requires_resource_types(temp_mimic_data_dir):
    """MimicOnFHIRLoader raises ValueError when resource_types is None."""
    loader = MimicOnFHIRLoader()

    with pytest.raises(ValueError, match="resource_types parameter is required"):
        loader.load(data_dir=str(temp_mimic_data_dir))


def test_mimic_loader_raises_error_for_missing_data_path():
    """MimicOnFHIRLoader raises FileNotFoundError when data path doesn't exist."""
    loader = MimicOnFHIRLoader()

    with pytest.raises(FileNotFoundError):
        loader.load(data_dir="/nonexistent/path", resource_types=["MimicMedication"])


def test_mimic_loader_raises_error_for_missing_resource_file(temp_mimic_data_dir):
    """MimicOnFHIRLoader raises FileNotFoundError when resource file doesn't exist."""
    loader = MimicOnFHIRLoader()

    with pytest.raises(FileNotFoundError, match="Resource file not found"):
        loader.load(
            data_dir=str(temp_mimic_data_dir), resource_types=["MimicMedication"]
        )


def test_mimic_loader_loads_single_resource_type(
    temp_mimic_data_dir, mock_medication_resources
):
    """MimicOnFHIRLoader loads and validates single resource type."""
    # Create mock data file
    fhir_dir = temp_mimic_data_dir / "fhir"
    create_ndjson_gz_file(
        fhir_dir / "MimicMedication.ndjson.gz", mock_medication_resources
    )

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir), resource_types=["MimicMedication"]
    )

    assert isinstance(result, dict)
    assert "medicationstatement" in result
    # Result dict contains a Bundle
    bundle = result["medicationstatement"]
    assert type(bundle).__name__ == "Bundle"
    assert len(bundle.entry) == 2
    assert bundle.entry[0].resource.id == "med-1"


def test_mimic_loader_loads_multiple_resource_types(
    temp_mimic_data_dir, mock_medication_resources, mock_condition_resources
):
    """MimicOnFHIRLoader loads multiple resource types and groups by FHIR type."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    create_ndjson_gz_file(
        fhir_dir / "MimicMedication.ndjson.gz", mock_medication_resources
    )
    create_ndjson_gz_file(
        fhir_dir / "MimicCondition.ndjson.gz", mock_condition_resources
    )

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir),
        resource_types=["MimicMedication", "MimicCondition"],
    )

    assert "medicationstatement" in result
    assert "condition" in result
    # Each result value is a Bundle
    med_bundle = result["medicationstatement"]
    cond_bundle = result["condition"]
    assert len(med_bundle.entry) == 2
    assert len(cond_bundle.entry) == 1


@pytest.mark.parametrize("sample_size,expected_count", [(1, 1), (2, 2)])
def test_mimic_loader_sampling_behavior(
    temp_mimic_data_dir, mock_medication_resources, sample_size, expected_count
):
    """MimicOnFHIRLoader samples specified number of resources."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    create_ndjson_gz_file(
        fhir_dir / "MimicMedication.ndjson.gz", mock_medication_resources
    )

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir),
        resource_types=["MimicMedication"],
        sample_size=sample_size,
    )

    bundle = result["medicationstatement"]
    assert len(bundle.entry) == expected_count


def test_mimic_loader_deterministic_sampling_with_seed(
    temp_mimic_data_dir, mock_medication_resources
):
    """MimicOnFHIRLoader produces consistent results with random_seed."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    create_ndjson_gz_file(
        fhir_dir / "MimicMedication.ndjson.gz", mock_medication_resources
    )

    loader = MimicOnFHIRLoader()
    result1 = loader.load(
        data_dir=str(temp_mimic_data_dir),
        resource_types=["MimicMedication"],
        sample_size=1,
        random_seed=42,
    )
    result2 = loader.load(
        data_dir=str(temp_mimic_data_dir),
        resource_types=["MimicMedication"],
        sample_size=1,
        random_seed=42,
    )

    bundle1 = result1["medicationstatement"]
    bundle2 = result2["medicationstatement"]
    assert bundle1.entry[0].resource.id == bundle2.entry[0].resource.id


def test_mimic_loader_handles_malformed_json(temp_mimic_data_dir):
    """MimicOnFHIRLoader skips malformed JSON lines and continues processing."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    file_path = fhir_dir / "MimicMedication.ndjson.gz"

    # Create file with mix of valid and malformed JSON
    with gzip.open(file_path, "wt") as f:
        f.write('{"invalid json\n')  # Malformed
        f.write(
            json.dumps(
                {
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
                    "subject": {"reference": "Patient/123"},
                }
            )
            + "\n"
        )  # Valid

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir), resource_types=["MimicMedication"]
    )

    # Should load the valid resource despite malformed line
    bundle = result["medicationstatement"]
    assert len(bundle.entry) == 1


def test_mimic_loader_raises_error_for_invalid_fhir_resources(temp_mimic_data_dir):
    """Loader validates FHIR resources and raises error for invalid data."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    file_path = fhir_dir / "MimicMedication.ndjson.gz"

    # Create file with invalid FHIR resource (missing required fields)
    invalid_resources = [
        {
            "resourceType": "MedicationStatement",
            "id": "med-1",
        },  # Missing required fields
    ]

    with gzip.open(file_path, "wt") as f:
        for resource in invalid_resources:
            f.write(json.dumps(resource) + "\n")

    loader = MimicOnFHIRLoader()

    # FHIR validation now catches the invalid resource
    with pytest.raises(Exception):
        loader.load(
            data_dir=str(temp_mimic_data_dir), resource_types=["MimicMedication"]
        )


def test_mimic_loader_skips_resources_without_resource_type(temp_mimic_data_dir):
    """MimicOnFHIRLoader skips resources missing resourceType field."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    file_path = fhir_dir / "MimicMedication.ndjson.gz"

    resources = [
        {"id": "med-1", "status": "recorded"},  # No resourceType
        {
            "resourceType": "MedicationStatement",
            "id": "med-2",
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
            "subject": {"reference": "Patient/123"},
        },
    ]

    create_ndjson_gz_file(file_path, resources)

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir), resource_types=["MimicMedication"]
    )

    # Should only load the valid resource
    bundle = result["medicationstatement"]
    assert len(bundle.entry) == 1


def test_mimic_loader_as_dict_returns_plain_dict(
    temp_mimic_data_dir, mock_medication_resources
):
    """MimicOnFHIRLoader with as_dict=True returns plain dict (not Pydantic Bundle)."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    create_ndjson_gz_file(
        fhir_dir / "MimicMedication.ndjson.gz", mock_medication_resources
    )

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir),
        resource_types=["MimicMedication"],
        as_dict=True,
    )

    # Should return a plain dict, not Dict[str, Bundle]
    assert isinstance(result, dict)
    assert "type" in result
    assert result["type"] == "collection"
    assert "entry" in result
    assert isinstance(result["entry"], list)
    assert len(result["entry"]) == 2


def test_mimic_loader_as_dict_combines_multiple_resource_types(
    temp_mimic_data_dir, mock_medication_resources, mock_condition_resources
):
    """MimicOnFHIRLoader with as_dict=True combines all resources into single bundle."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    create_ndjson_gz_file(
        fhir_dir / "MimicMedication.ndjson.gz", mock_medication_resources
    )
    create_ndjson_gz_file(
        fhir_dir / "MimicCondition.ndjson.gz", mock_condition_resources
    )

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir),
        resource_types=["MimicMedication", "MimicCondition"],
        as_dict=True,
    )

    # Should be a single bundle dict with all resources combined
    assert isinstance(result, dict)
    assert result["type"] == "collection"
    assert len(result["entry"]) == 3  # 2 medications + 1 condition

    # Verify resource types are mixed
    resource_types = {entry["resource"]["resourceType"] for entry in result["entry"]}
    assert resource_types == {"MedicationStatement", "Condition"}


def test_mimic_loader_default_returns_validated_bundles(
    temp_mimic_data_dir, mock_medication_resources, mock_condition_resources
):
    """MimicOnFHIRLoader with as_dict=False (default) returns validated Bundle objects."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    create_ndjson_gz_file(
        fhir_dir / "MimicMedication.ndjson.gz", mock_medication_resources
    )
    create_ndjson_gz_file(
        fhir_dir / "MimicCondition.ndjson.gz", mock_condition_resources
    )

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir),
        resource_types=["MimicMedication", "MimicCondition"],
        as_dict=False,  # Explicit default
    )

    # Should return Dict[str, Bundle] with validated Pydantic objects
    assert isinstance(result, dict)
    assert "medicationstatement" in result
    assert "condition" in result

    # Each value should be a Pydantic Bundle
    assert type(result["medicationstatement"]).__name__ == "Bundle"
    assert type(result["condition"]).__name__ == "Bundle"
    assert len(result["medicationstatement"].entry) == 2
    assert len(result["condition"].entry) == 1


def test_mimic_loader_as_dict_structure_matches_fhir_bundle(
    temp_mimic_data_dir, mock_medication_resources
):
    """MimicOnFHIRLoader with as_dict=True produces valid FHIR Bundle structure."""
    fhir_dir = temp_mimic_data_dir / "fhir"
    create_ndjson_gz_file(
        fhir_dir / "MimicMedication.ndjson.gz", mock_medication_resources
    )

    loader = MimicOnFHIRLoader()
    result = loader.load(
        data_dir=str(temp_mimic_data_dir),
        resource_types=["MimicMedication"],
        as_dict=True,
    )

    # Verify FHIR Bundle structure
    assert result["type"] == "collection"
    assert isinstance(result["entry"], list)

    # Each entry should have resource field
    for entry in result["entry"]:
        assert "resource" in entry
        assert "resourceType" in entry["resource"]
        assert entry["resource"]["resourceType"] == "MedicationStatement"
