"""Tests for FHIR sandbox seeder utilities."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from healthchain.sandbox.seeders import (
    _as_transaction_bundle,
    _normalise_base_url,
    _patient_ids_from_response,
    seed_from_directory,
    seed_from_file,
)


# --- _normalise_base_url ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://api.medplum.com/fhir/R4", "https://api.medplum.com/fhir/R4"),
        ("https://api.medplum.com/fhir/R4/", "https://api.medplum.com/fhir/R4"),
        ("http://localhost:8103/fhir/R4", "http://localhost:8103/fhir/R4"),
        ("fhir://api.medplum.com/fhir/R4", "https://api.medplum.com/fhir/R4"),
        ("fhir://api.medplum.com/fhir/R4/", "https://api.medplum.com/fhir/R4"),
    ],
)
def test_normalise_base_url_strips_trailing_slash_and_normalises_scheme(raw, expected):
    assert _normalise_base_url(raw) == expected


def test_normalise_base_url_raises_for_unsupported_scheme():
    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        _normalise_base_url("ftp://example.com/fhir")


def test_normalise_base_url_raises_for_missing_scheme():
    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        _normalise_base_url("example.com/fhir")


# --- _as_transaction_bundle ---


def test_as_transaction_bundle_passes_through_existing_bundle():
    bundle = {"resourceType": "Bundle", "type": "transaction", "entry": []}
    result = _as_transaction_bundle(bundle)
    assert result is bundle


def test_as_transaction_bundle_wraps_single_resource():
    resource = {"resourceType": "Patient", "id": "p1"}
    result = _as_transaction_bundle(resource)
    assert result["resourceType"] == "Bundle"
    assert result["type"] == "transaction"
    assert len(result["entry"]) == 1
    assert result["entry"][0]["resource"] == resource
    assert result["entry"][0]["request"] == {"method": "POST", "url": "Patient"}


def test_as_transaction_bundle_wraps_list_of_resources():
    resources = [
        {"resourceType": "Patient", "id": "p1"},
        {"resourceType": "Condition", "id": "c1"},
    ]
    result = _as_transaction_bundle(resources)
    assert result["resourceType"] == "Bundle"
    assert result["type"] == "transaction"
    assert len(result["entry"]) == 2
    assert result["entry"][0]["request"]["url"] == "Patient"
    assert result["entry"][1]["request"]["url"] == "Condition"


def test_as_transaction_bundle_uses_resource_type_as_url():
    resource = {"resourceType": "Observation", "id": "o1"}
    result = _as_transaction_bundle(resource)
    assert result["entry"][0]["request"]["url"] == "Observation"


def test_as_transaction_bundle_falls_back_to_resource_for_missing_resource_type():
    resource = {"id": "x1"}  # No resourceType
    result = _as_transaction_bundle(resource)
    assert result["entry"][0]["request"]["url"] == "Resource"


# --- _patient_ids_from_response ---


def test_patient_ids_from_response_extracts_ids_from_location():
    response = {
        "resourceType": "Bundle",
        "type": "transaction-response",
        "entry": [
            {"response": {"location": "Patient/abc123/_history/1"}},
            {"response": {"location": "Condition/xyz789/_history/1"}},
            {"response": {"location": "Patient/def456/_history/1"}},
        ],
    }
    ids = _patient_ids_from_response(response)
    assert ids == ["abc123", "def456"]


def test_patient_ids_from_response_returns_empty_for_no_patients():
    response = {
        "entry": [
            {"response": {"location": "Condition/xyz789/_history/1"}},
        ]
    }
    assert _patient_ids_from_response(response) == []


def test_patient_ids_from_response_returns_empty_for_empty_bundle():
    assert _patient_ids_from_response({}) == []
    assert _patient_ids_from_response({"entry": []}) == []


def test_patient_ids_from_response_handles_missing_location():
    response = {
        "entry": [
            {"response": {}},
            {"response": {"location": "Patient/abc123/_history/1"}},
        ]
    }
    ids = _patient_ids_from_response(response)
    assert ids == ["abc123"]


# --- seed_from_file ---


@pytest.fixture
def mock_fhir_auth_config():
    config = MagicMock()
    config.base_url = "https://api.medplum.com/fhir/R4"
    oauth_config = MagicMock()
    config.to_oauth2_config.return_value = oauth_config
    return config


@pytest.fixture
def mock_token_manager():
    manager = MagicMock()
    manager.get_access_token.return_value = "test-token"
    return manager


def _make_response_bundle(patient_id: str) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "transaction-response",
        "entry": [{"response": {"location": f"Patient/{patient_id}/_history/1"}}],
    }


def test_seed_from_file_posts_bundle_and_returns_patient_ids(
    mock_fhir_auth_config, mock_token_manager
):
    patient_bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {"resourceType": "Patient", "id": "p1"},
                "request": {"method": "POST", "url": "Patient"},
            }
        ],
    }
    mock_response = MagicMock()
    mock_response.json.return_value = _make_response_bundle("abc123")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "bundle.json"
        path.write_text(json.dumps(patient_bundle))

        with (
            patch(
                "healthchain.sandbox.seeders.OAuth2TokenManager",
                return_value=mock_token_manager,
            ),
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = seed_from_file(mock_fhir_auth_config, path)

    assert result == ["abc123"]
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"] == patient_bundle


def test_seed_from_file_wraps_single_resource_before_posting(
    mock_fhir_auth_config, mock_token_manager
):
    single_resource = {"resourceType": "Patient", "id": "p1"}
    mock_response = MagicMock()
    mock_response.json.return_value = _make_response_bundle("abc123")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "patient.json"
        path.write_text(json.dumps(single_resource))

        with (
            patch(
                "healthchain.sandbox.seeders.OAuth2TokenManager",
                return_value=mock_token_manager,
            ),
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = seed_from_file(mock_fhir_auth_config, path)

    assert result == ["abc123"]
    posted_bundle = mock_client.post.call_args[1]["json"]
    assert posted_bundle["resourceType"] == "Bundle"
    assert posted_bundle["type"] == "transaction"


# --- seed_from_directory ---


def test_seed_from_directory_processes_all_json_files_alphabetically(
    mock_fhir_auth_config, mock_token_manager
):
    files = {
        "alpha.json": {"resourceType": "Patient", "id": "p1"},
        "beta.json": {"resourceType": "Patient", "id": "p2"},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        for name, content in files.items():
            (tmppath / name).write_text(json.dumps(content))

        call_count = 0

        def fake_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.json.return_value = _make_response_bundle(f"id{call_count}")
            return mock_resp

        with (
            patch(
                "healthchain.sandbox.seeders.OAuth2TokenManager",
                return_value=mock_token_manager,
            ),
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.side_effect = fake_post

            result = seed_from_directory(mock_fhir_auth_config, tmppath)

    assert set(result.keys()) == {"alpha", "beta"}
    assert mock_client.post.call_count == 2


def test_seed_from_directory_returns_stem_to_patient_ids_mapping(
    mock_fhir_auth_config, mock_token_manager
):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / "bundle_a.json").write_text(
            json.dumps({"resourceType": "Patient", "id": "p1"})
        )

        mock_response = MagicMock()
        mock_response.json.return_value = _make_response_bundle("patient-xyz")

        with (
            patch(
                "healthchain.sandbox.seeders.OAuth2TokenManager",
                return_value=mock_token_manager,
            ),
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = seed_from_directory(mock_fhir_auth_config, tmppath)

    assert result == {"bundle_a": ["patient-xyz"]}


def test_seed_from_directory_returns_empty_dict_for_empty_directory(
    mock_fhir_auth_config, mock_token_manager
):
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch(
            "healthchain.sandbox.seeders.OAuth2TokenManager",
            return_value=mock_token_manager,
        ):
            result = seed_from_directory(mock_fhir_auth_config, Path(tmpdir))

    assert result == {}
