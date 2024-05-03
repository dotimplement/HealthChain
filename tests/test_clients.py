import pytest
from unittest.mock import Mock, patch
from healthchain.clients import EHRClient


@pytest.fixture
def mock_function():
    return Mock()


@pytest.fixture
def mock_workflow():
    return Mock()


@pytest.fixture
def mock_use_case():
    mock = Mock()
    mock.construct_request = Mock(
        return_value=Mock(model_dump_json=Mock(return_value="{}"))
    )
    return mock


@pytest.fixture
def ehr_client(mock_function, mock_workflow, mock_use_case):
    return EHRClient(mock_function, mock_workflow, mock_use_case)


def test_init(ehr_client, mock_function, mock_workflow, mock_use_case):
    assert ehr_client.data_generator_func == mock_function
    assert ehr_client.workflow == mock_workflow
    assert ehr_client.use_case == mock_use_case
    assert ehr_client.request_data == []


def test_generate_request(ehr_client, mock_use_case):
    ehr_client.generate_request(1, 2, test="data")
    mock_use_case.construct_request.assert_called_once()
    assert len(ehr_client.request_data) == 1


@patch("requests.post")
def test_send_request(mock_post, ehr_client):
    # Configure the mock to return a successful response
    mock_post.return_value.json = Mock(return_value={"status": "success"})
    mock_post.return_value.status_code = 200
    ehr_client.request_data = [
        Mock(model_dump_json=Mock(return_value="{}")) for _ in range(2)
    ]

    responses = ehr_client.send_request("http://fakeurl.com")

    assert mock_post.call_count == 2
    assert all(response["status"] == "success" for response in responses)

    # Test error handling
    mock_post.side_effect = Exception("Failed to connect")
    responses = ehr_client.send_request("http://fakeurl.com")
    assert {} in responses  # Check if empty dict was appended due to the error


def test_logging_on_send_request_error(caplog, ehr_client):
    with patch("requests.post") as mock_post:
        mock_post.side_effect = Exception("Failed to connect")
        ehr_client.request_data = [Mock(model_dump_json=Mock(return_value="{}"))]
        ehr_client.send_request("http://fakeurl.com")
        assert "Error sending request: Failed to connect" in caplog.text
