import pytest

from healthchain.sandbox import SandboxClient


def test_load_from_registry_unknown_dataset():
    """load_from_registry raises ValueError for unknown datasets."""
    client = SandboxClient(api_url="http://localhost:8000", endpoint="/test")

    with pytest.raises(ValueError, match="Unknown dataset"):
        client.load_from_registry("nonexistent-dataset")


def test_load_from_path_single_xml_file(tmp_path):
    """load_from_path loads single CDA XML file."""
    # Create test CDA file
    cda_file = tmp_path / "test_cda.xml"
    cda_file.write_text("<ClinicalDocument>Test CDA</ClinicalDocument>")

    client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/notereader/fhir/", protocol="soap"
    )

    result = client.load_from_path(str(cda_file))

    assert result is client
    assert len(client.request_data) == 1


def test_load_from_path_directory_with_pattern(tmp_path):
    """load_from_path loads multiple files from directory with pattern."""
    # Create test CDA files
    (tmp_path / "note1.xml").write_text("<ClinicalDocument>Note 1</ClinicalDocument>")
    (tmp_path / "note2.xml").write_text("<ClinicalDocument>Note 2</ClinicalDocument>")
    (tmp_path / "other.txt").write_text("Not XML")

    client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/notereader/fhir/", protocol="soap"
    )

    client.load_from_path(str(tmp_path), pattern="*.xml")

    assert len(client.request_data) == 2


def test_load_from_path_directory_all_files(tmp_path):
    """load_from_path loads all matching files from directory."""
    # Create test files
    (tmp_path / "note1.xml").write_text("<ClinicalDocument>Note 1</ClinicalDocument>")
    (tmp_path / "note2.xml").write_text("<ClinicalDocument>Note 2</ClinicalDocument>")

    client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/notereader/fhir/", protocol="soap"
    )

    client.load_from_path(str(tmp_path))

    assert len(client.request_data) == 2


def test_load_from_path_error_handling(tmp_path):
    """load_from_path raises FileNotFoundError for nonexistent path."""
    client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/notereader/fhir/", protocol="soap"
    )

    with pytest.raises(FileNotFoundError):
        client.load_from_path("/nonexistent/path.xml")

    with pytest.raises(ValueError, match="No files found"):
        client.load_from_path(str(tmp_path), pattern="*.xml")


def test_load_free_text_generates_data(tmp_path):
    """load_free_text generates synthetic data from CSV."""
    # Create test CSV
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("text\nSample discharge note\n")

    client = SandboxClient(api_url="http://localhost:8000", endpoint="/test")

    client.load_free_text(
        csv_path=str(csv_file),
        column_name="text",
        workflow="encounter-discharge",
        random_seed=42,
    )
    assert len(client.request_data) > 0


def test_send_requests_without_data():
    """send_requests raises RuntimeError if no data is loaded."""
    client = SandboxClient(api_url="http://localhost:8000", endpoint="/test")

    with pytest.raises(RuntimeError, match="No requests to send"):
        client.send_requests()


def test_save_responses_without_responses():
    """save_responses raises RuntimeError if no responses available."""
    client = SandboxClient(api_url="http://localhost:8000", endpoint="/test")

    with pytest.raises(RuntimeError, match="No responses to save"):
        client.save_responses()


def test_get_status():
    """get_status returns client status information."""
    client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/test", workflow="patient-view"
    )

    status = client.get_status()

    assert "sandbox_id" in status
    assert status["api_url"] == "http://localhost:8000"
    assert status["endpoint"] == "/test"
    assert status["protocol"] == "REST"
    assert status["workflow"] == "patient-view"
    assert status["requests_queued"] == 0
    assert status["responses_received"] == 0


def test_repr():
    """__repr__ returns meaningful string representation."""
    client = SandboxClient(api_url="http://localhost:8000", endpoint="/test")

    repr_str = repr(client)

    assert "SandboxClient" in repr_str
    assert "http://localhost:8000" in repr_str
    assert "/test" in repr_str
