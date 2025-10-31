"""Tests for sandbox utility functions."""

import pytest
import json

from unittest.mock import patch

from healthchain.sandbox.utils import (
    generate_filename,
    save_file,
    ensure_directory_exists,
    save_data_to_directory,
)


def test_generate_filename_format():
    """generate_filename creates properly formatted filenames with timestamp and identifiers."""
    with patch("healthchain.sandbox.utils.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "2024-01-15_10:30:45"

        # Test JSON filename
        filename = generate_filename("request", "abc123def456", 0, "json")
        assert filename == "2024-01-15_10:30:45_sandbox_abc123de_request_0.json"

        # Test XML filename
        filename = generate_filename("response", "xyz789abc123", 5, "xml")
        assert filename == "2024-01-15_10:30:45_sandbox_xyz789ab_response_5.xml"


def test_save_file_handles_json_and_xml(tmp_path):
    """save_file correctly saves JSON and XML data with proper formatting."""
    sandbox_id = "test123"

    # Test JSON save
    json_data = {"key": "value", "nested": {"data": 123}}
    save_file(json_data, "request", sandbox_id, 0, tmp_path, "json")

    json_files = list(tmp_path.glob("*_request_0.json"))
    assert len(json_files) == 1
    with open(json_files[0]) as f:
        loaded = json.load(f)
        assert loaded == json_data

    # Test XML save
    xml_data = "<root><element>content</element></root>"
    save_file(xml_data, "response", sandbox_id, 1, tmp_path, "xml")

    xml_files = list(tmp_path.glob("*_response_1.xml"))
    assert len(xml_files) == 1
    with open(xml_files[0]) as f:
        assert f.read() == xml_data


def test_save_file_rejects_unsupported_extensions(tmp_path):
    """save_file raises ValueError for unsupported file extensions."""
    with pytest.raises(ValueError, match="Unsupported extension: txt"):
        save_file("data", "request", "test123", 0, tmp_path, "txt")


def test_ensure_directory_exists_creates_nested_paths(tmp_path):
    """ensure_directory_exists creates nested directory structures."""
    nested_path = tmp_path / "level1" / "level2" / "level3"

    result = ensure_directory_exists(nested_path)

    assert result.exists()
    assert result.is_dir()
    assert result == nested_path


def test_ensure_directory_exists_idempotent(tmp_path):
    """ensure_directory_exists safely handles already existing directories."""
    test_dir = tmp_path / "existing"
    test_dir.mkdir()

    # Should not raise error
    result = ensure_directory_exists(test_dir)
    assert result.exists()


def test_save_data_to_directory_batch_processing(tmp_path):
    """save_data_to_directory saves multiple data items with proper indexing."""
    data_list = [
        {"request": 1, "data": "first"},
        {"request": 2, "data": "second"},
        {"request": 3, "data": "third"},
    ]

    save_data_to_directory(data_list, "request", "test123", tmp_path, "json")

    # Verify all files created
    json_files = sorted(tmp_path.glob("*_request_*.json"))
    assert len(json_files) == 3

    # Verify content
    for idx, file_path in enumerate(json_files):
        with open(file_path) as f:
            loaded = json.load(f)
            assert loaded["request"] == idx + 1


def test_save_data_to_directory_handles_errors_gracefully(tmp_path, caplog):
    """save_data_to_directory logs errors but continues processing remaining items."""
    # Mix valid and invalid data
    data_list = [
        {"valid": "data1"},
        None,  # Will cause error during JSON serialization
        {"valid": "data2"},
    ]

    with patch("healthchain.sandbox.utils.save_file") as mock_save:
        # Make second save fail
        mock_save.side_effect = [None, Exception("Save failed"), None]

        save_data_to_directory(data_list, "request", "test123", tmp_path, "json")

        # Should attempt to save all three
        assert mock_save.call_count == 3
