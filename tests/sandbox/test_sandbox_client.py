import pytest
import json
from unittest.mock import Mock, patch

from healthchain.sandbox import SandboxClient


def test_load_from_registry_unknown_dataset():
    """load_from_registry raises ValueError for unknown datasets."""
    client = SandboxClient(url="http://localhost:8000/test", workflow="patient-view")

    with pytest.raises(ValueError, match="Unknown dataset"):
        client.load_from_registry("nonexistent-dataset", data_dir="/test")


def test_load_from_path_single_xml_file(tmp_path):
    """load_from_path loads single CDA XML file."""
    # Create test CDA file
    cda_file = tmp_path / "test_cda.xml"
    cda_file.write_text("<ClinicalDocument>Test CDA</ClinicalDocument>")

    client = SandboxClient(
        url="http://localhost:8000/notereader/?wsdl",
        workflow="sign-note-inpatient",
        protocol="soap",
    )

    result = client.load_from_path(str(cda_file))

    assert result is client
    assert len(client.requests) == 1


def test_load_from_path_directory_with_pattern(tmp_path):
    """load_from_path loads multiple files from directory with pattern."""
    # Create test CDA files
    (tmp_path / "note1.xml").write_text("<ClinicalDocument>Note 1</ClinicalDocument>")
    (tmp_path / "note2.xml").write_text("<ClinicalDocument>Note 2</ClinicalDocument>")
    (tmp_path / "other.txt").write_text("Not XML")

    client = SandboxClient(
        url="http://localhost:8000/notereader/?wsdl",
        workflow="sign-note-inpatient",
        protocol="soap",
    )

    client.load_from_path(str(tmp_path), pattern="*.xml")

    assert len(client.requests) == 2


def test_load_from_path_directory_all_files(tmp_path):
    """load_from_path loads all matching files from directory."""
    # Create test files
    (tmp_path / "note1.xml").write_text("<ClinicalDocument>Note 1</ClinicalDocument>")
    (tmp_path / "note2.xml").write_text("<ClinicalDocument>Note 2</ClinicalDocument>")

    client = SandboxClient(
        url="http://localhost:8000/notereader/?wsdl",
        workflow="sign-note-inpatient",
        protocol="soap",
    )

    client.load_from_path(str(tmp_path))

    assert len(client.requests) == 2


def test_load_from_path_error_handling(tmp_path):
    """load_from_path raises FileNotFoundError for nonexistent path."""
    client = SandboxClient(
        url="http://localhost:8000/notereader/?wsdl",
        workflow="sign-note-inpatient",
        protocol="soap",
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

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="encounter-discharge",
    )

    client.load_free_text(
        csv_path=str(csv_file),
        column_name="text",
        random_seed=42,
    )
    assert len(client.requests) > 0


def test_load_free_text_without_synthetic_data(tmp_path):
    """load_free_text can generate data without synthetic resources."""
    # Create test CSV
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("text\nSample discharge note\nAnother note\n")

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="encounter-discharge",
    )

    client.load_free_text(
        csv_path=str(csv_file),
        column_name="text",
        generate_synthetic=False,
        random_seed=42,
    )

    assert len(client.requests) > 0
    # Verify request was created (but without checking prefetch content details)
    assert client.requests[0].hook == "encounter-discharge"


def test_send_requests_without_data():
    """send_requests raises RuntimeError if no data is loaded."""
    client = SandboxClient(url="http://localhost:8000/test", workflow="patient-view")

    with pytest.raises(RuntimeError, match="No requests to send"):
        client.send_requests()


def test_save_results_without_responses():
    """save_results raises RuntimeError if no responses available."""
    client = SandboxClient(url="http://localhost:8000/test", workflow="patient-view")

    with pytest.raises(RuntimeError, match="No responses to save"):
        client.save_results()


def test_get_status():
    """get_status returns client status information."""
    client = SandboxClient(url="http://localhost:8000/test", workflow="patient-view")

    status = client.get_status()

    assert "sandbox_id" in status
    assert status["url"] == "http://localhost:8000/test"
    assert status["protocol"] == "REST"
    assert status["workflow"] == "patient-view"
    assert status["requests_queued"] == 0
    assert status["responses_received"] == 0


def test_repr():
    """__repr__ returns meaningful string representation."""
    client = SandboxClient(url="http://localhost:8000/test", workflow="patient-view")

    repr_str = repr(client)

    assert "SandboxClient" in repr_str
    assert "http://localhost:8000/test" in repr_str


def test_load_from_path_json_prefetch_file(tmp_path):
    """load_from_path loads and validates JSON Prefetch files."""
    from healthchain.fhir import create_bundle

    # Create valid Prefetch JSON
    json_file = tmp_path / "prefetch.json"
    prefetch_data = {"prefetch": {"patient": create_bundle().model_dump()}}
    json_file.write_text(json.dumps(prefetch_data))

    client = SandboxClient(url="http://localhost:8000/test", workflow="patient-view")

    client.load_from_path(str(json_file))

    assert len(client.requests) == 1
    assert client.requests[0].hook == "patient-view"


def test_load_from_path_invalid_json_prefetch(tmp_path):
    """load_from_path processes JSON data for prefetch."""
    json_file = tmp_path / "data.json"
    json_file.write_text('{"not_prefetch": "data"}')

    client = SandboxClient(url="http://localhost:8000/test", workflow="patient-view")

    # Should load the JSON data without error since we're using plain dicts now
    client.load_from_path(str(json_file))
    assert len(client.requests) == 1


def test_save_results_distinguishes_protocols(tmp_path):
    """save_results uses correct file extension based on protocol."""
    from healthchain.fhir import create_bundle

    # Test REST/JSON protocol
    rest_client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
        protocol="rest",
    )
    prefetch = {"patient": create_bundle()}
    rest_client._construct_request(prefetch)
    rest_client.responses = [{"cards": []}]

    rest_dir = tmp_path / "rest"
    rest_client.save_results(rest_dir)

    assert len(list(rest_dir.glob("**/*.json"))) > 0
    assert len(list(rest_dir.glob("**/*.xml"))) == 0

    # Test SOAP/XML protocol
    soap_client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="sign-note-inpatient",
        protocol="soap",
    )
    soap_client._construct_request("<doc>test</doc>")
    soap_client.responses = ["<response>data</response>"]

    soap_dir = tmp_path / "soap"
    soap_client.save_results(soap_dir)

    assert len(list(soap_dir.glob("**/*.xml"))) > 0
    assert len(list(soap_dir.glob("**/*.json"))) == 0


@pytest.mark.parametrize(
    "workflow,protocol,should_fail",
    [
        ("patient-view", "rest", False),  # Valid CDS workflow with REST
        ("encounter-discharge", "rest", False),  # Valid CDS workflow with REST
        ("sign-note-inpatient", "soap", False),  # Valid ClinDoc workflow with SOAP
        ("patient-view", "soap", True),  # CDS workflow with SOAP - invalid
        ("sign-note-inpatient", "rest", True),  # ClinDoc workflow with REST - invalid
    ],
)
def test_workflow_protocol_validation(workflow, protocol, should_fail):
    """SandboxClient validates workflow-protocol compatibility at initialization."""
    if should_fail:
        with pytest.raises(ValueError, match="not compatible"):
            SandboxClient(
                url="http://localhost:8000/test",
                workflow=workflow,
                protocol=protocol,
            )
    else:
        client = SandboxClient(
            url="http://localhost:8000/test",
            workflow=workflow,
            protocol=protocol,
        )
        assert client.workflow.value == workflow


def test_clear_requests():
    """clear_requests empties the request queue."""
    from healthchain.fhir import create_bundle

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    )

    # Load some data
    prefetch = {"patient": create_bundle()}
    client._construct_request(prefetch)
    assert len(client.requests) == 1

    # Clear and verify
    result = client.clear_requests()
    assert result is client  # Method chaining
    assert len(client.requests) == 0


def test_preview_requests_provides_metadata():
    """preview_requests returns summary metadata without sending requests."""
    from healthchain.fhir import create_bundle

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    )

    # Load data
    prefetch = {"patient": create_bundle()}
    client._construct_request(prefetch)
    client._construct_request(prefetch)

    # Preview without sending
    previews = client.preview_requests()

    assert len(previews) == 2
    assert previews[0]["index"] == 0
    assert previews[0]["type"] == "CDSRequest"
    assert (
        previews[0]["protocol"] == "REST"
    )  # Protocol is uppercase in actual implementation
    assert previews[0]["hook"] == "patient-view"


def test_preview_requests_respects_limit():
    """preview_requests limits returned results when limit specified."""
    from healthchain.fhir import create_bundle

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    )

    # Load multiple requests
    prefetch = {"patient": create_bundle()}
    for _ in range(5):
        client._construct_request(prefetch)

    previews = client.preview_requests(limit=2)
    assert len(previews) == 2


@pytest.mark.parametrize(
    "format_type,check",
    [
        ("dict", lambda data: isinstance(data, list) and isinstance(data[0], dict)),
        ("json", lambda data: isinstance(data, str) and json.loads(data)),
    ],
)
def test_get_request_data_formats(format_type, check):
    """get_request_data returns data in specified format."""
    from healthchain.fhir import create_bundle

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    )

    prefetch = {"patient": create_bundle()}
    client._construct_request(prefetch)

    data = client.get_request_data(format=format_type)

    assert check(data)


def test_get_request_data_invalid_format():
    """get_request_data raises ValueError for invalid format."""
    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    )

    with pytest.raises(ValueError, match="Invalid format"):
        client.get_request_data(format="invalid")


def test_context_manager_auto_saves_on_success(tmp_path):
    """Context manager auto-saves results when responses exist and no exception."""
    from healthchain.fhir import create_bundle

    with SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    ) as client:
        prefetch = {"patient": create_bundle()}
        client._construct_request(prefetch)
        # Simulate responses
        client.responses = [{"cards": []}]

    # Auto-save should have been triggered (saves to "./output/" by default)


def test_context_manager_no_save_without_responses(tmp_path):
    """Context manager does not save if no responses generated."""
    with SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    ) as client:
        # No requests or responses
        pass

    # Should exit cleanly without trying to save
    assert len(client.responses) == 0


def test_context_manager_no_save_on_exception():
    """Context manager does not save if exception occurs."""
    with pytest.raises(RuntimeError):
        with SandboxClient(
            url="http://localhost:8000/test",
            workflow="patient-view",
        ) as client:
            client.responses = [{"cards": []}]
            raise RuntimeError("Test exception")

    # Should exit without attempting save


@patch("httpx.Client")
def test_send_requests_rest_success(mock_client_class):
    """send_requests successfully processes REST/CDS Hooks requests."""
    from healthchain.fhir import create_bundle

    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = {"cards": [{"summary": "Test card"}]}
    mock_response.raise_for_status = Mock()

    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    mock_client_class.return_value = mock_client

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    )

    prefetch = {"patient": create_bundle()}
    client._construct_request(prefetch)

    responses = client.send_requests()

    assert len(responses) == 1
    assert responses[0]["cards"][0]["summary"] == "Test card"
    assert mock_client.post.called


@patch("httpx.Client")
def test_send_requests_soap_success(mock_client_class):
    """send_requests successfully processes SOAP/CDA requests."""
    # Mock successful response
    mock_response = Mock()
    mock_response.text = "<ClinicalDocument>Response</ClinicalDocument>"
    mock_response.raise_for_status = Mock()

    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    mock_client_class.return_value = mock_client

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="sign-note-inpatient",
        protocol="soap",
    )

    client._construct_request("<ClinicalDocument>Test</ClinicalDocument>")

    responses = client.send_requests()

    assert len(responses) == 1
    # Response is processed by CdaResponse which may return empty dict if parsing fails
    assert isinstance(responses[0], (str, dict))
    assert mock_client.post.called


@patch("httpx.Client")
def test_send_requests_handles_multiple_requests(mock_client_class):
    """send_requests processes multiple queued requests sequentially."""
    from healthchain.fhir import create_bundle

    # Mock successful responses
    mock_response = Mock()
    mock_response.json.return_value = {"cards": []}
    mock_response.raise_for_status = Mock()

    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    mock_client_class.return_value = mock_client

    client = SandboxClient(
        url="http://localhost:8000/test",
        workflow="patient-view",
    )

    # Load multiple requests
    prefetch = {"patient": create_bundle()}
    client._construct_request(prefetch)
    client._construct_request(prefetch)
    client._construct_request(prefetch)

    responses = client.send_requests()

    assert len(responses) == 3
    assert mock_client.post.call_count == 3
