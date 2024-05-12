import pytest
import httpx
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


@pytest.mark.anyio
@patch(
    "healthchain.clients.httpx.AsyncClient.post",
    return_value=httpx.Response(200, json={"response": "test successful"}),
)
async def test_send_request(ehr_client):
    responses = await ehr_client.send_request("http://fakeurl.com")
    assert all(response["status"] == "success" for response in responses)


@pytest.mark.anyio
async def test_logging_on_send_request_error(caplog, ehr_client):
    with patch("healthchain.clients.httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = Exception("Failed to connect")
        ehr_client.request_data = [Mock(model_dump_json=Mock(return_value="{}"))]
        responses = await ehr_client.send_request("http://fakeurl.com")
        assert "Error sending request: Failed to connect" in caplog.text
        assert {} in responses
