import pytest
import json

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


def test_save_results_without_responses():
    """save_results raises RuntimeError if no responses available."""
    client = SandboxClient(api_url="http://localhost:8000", endpoint="/test")

    with pytest.raises(RuntimeError, match="No responses to save"):
        client.save_results()


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


def test_load_from_path_json_prefetch_file(tmp_path):
    """load_from_path loads and validates JSON Prefetch files."""
    from healthchain.fhir import create_bundle

    # Create valid Prefetch JSON
    json_file = tmp_path / "prefetch.json"
    prefetch_data = {"prefetch": {"patient": create_bundle().model_dump()}}
    json_file.write_text(json.dumps(prefetch_data))

    client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/test", workflow="patient-view"
    )

    client.load_from_path(str(json_file))

    assert len(client.request_data) == 1
    assert client.request_data[0].hook == "patient-view"


def test_load_from_path_json_without_workflow_fails(tmp_path):
    """load_from_path requires workflow for JSON Prefetch files."""
    json_file = tmp_path / "prefetch.json"
    json_file.write_text('{"prefetch": {}}')

    client = SandboxClient(api_url="http://localhost:8000", endpoint="/test")

    with pytest.raises(ValueError, match="Workflow must be specified"):
        client.load_from_path(str(json_file))


def test_load_from_path_invalid_json_prefetch(tmp_path):
    """load_from_path processes JSON data for prefetch."""
    json_file = tmp_path / "data.json"
    json_file.write_text('{"not_prefetch": "data"}')

    client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/test", workflow="patient-view"
    )

    # Should load the JSON data without error since we're using plain dicts now
    client.load_from_path(str(json_file))
    assert len(client.request_data) == 1


def test_save_results_distinguishes_protocols(tmp_path):
    """save_results uses correct file extension based on protocol."""
    from healthchain.fhir import create_bundle
    from healthchain.sandbox.workflows import Workflow

    # Test REST/JSON protocol
    rest_client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/test", protocol="rest"
    )
    prefetch = {"patient": create_bundle()}
    rest_client._construct_request(prefetch, Workflow.patient_view)
    rest_client.responses = [{"cards": []}]

    rest_dir = tmp_path / "rest"
    rest_client.save_results(rest_dir)

    assert len(list(rest_dir.glob("**/*.json"))) > 0
    assert len(list(rest_dir.glob("**/*.xml"))) == 0

    # Test SOAP/XML protocol
    soap_client = SandboxClient(
        api_url="http://localhost:8000", endpoint="/test", protocol="soap"
    )
    soap_client._construct_request("<doc>test</doc>", Workflow.sign_note_inpatient)
    soap_client.responses = ["<response>data</response>"]

    soap_dir = tmp_path / "soap"
    soap_client.save_results(soap_dir)

    assert len(list(soap_dir.glob("**/*.xml"))) > 0
    assert len(list(soap_dir.glob("**/*.json"))) == 0


def test_construct_request_requires_workflow_for_rest():
    """_construct_request raises ValueError if workflow missing for REST protocol."""
    client = SandboxClient(api_url="http://localhost:8000", endpoint="/test")
    from healthchain.fhir import create_bundle

    prefetch = {"patient": create_bundle()}

    with pytest.raises(ValueError, match="Workflow must be specified for REST"):
        client._construct_request(prefetch, None)
