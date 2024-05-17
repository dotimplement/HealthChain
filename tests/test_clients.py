import pytest
import httpx
from unittest.mock import Mock, patch


def test_init(ehr_client, mock_function, mock_workflow, mock_strategy):
    assert ehr_client.data_generator_func == mock_function
    assert ehr_client.workflow == mock_workflow
    assert ehr_client.strategy == mock_strategy
    assert ehr_client.request_data == []


def test_generate_request(ehr_client, mock_strategy):
    ehr_client.generate_request(1, 2, test="data")
    mock_strategy.construct_request.assert_called_once()
    assert len(ehr_client.request_data) == 1


@pytest.mark.anyio
@patch(
    "healthchain.clients.httpx.AsyncClient.post",
    return_value=httpx.Response(200, json={"response": "test successful"}),
)
async def test_send_request(ehr_client):
    ehr_client.request_data = [Mock(model_dump_json=Mock(return_value="{}"))]
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
