import pytest
import httpx

from unittest.mock import Mock, patch


@pytest.fixture
def mock_strategy():
    mock = Mock()
    mock.construct_request = Mock(
        return_value=Mock(model_dump_json=Mock(return_value="{}"))
    )
    return mock


def test_init(ehr_client, mock_function, mock_workflow, mock_strategy):
    assert ehr_client.data_generator_func == mock_function
    assert ehr_client.workflow == mock_workflow
    assert ehr_client.strategy == mock_strategy
    assert ehr_client.request_data == []


def test_generate_request(ehr_client, mock_strategy):
    ehr_client.generate_request(1, 2, test="data")
    mock_strategy.construct_request.assert_called_once()
    assert len(ehr_client.request_data) == 1


@pytest.mark.asyncio
@patch.object(
    httpx.AsyncClient,
    "post",
    return_value=httpx.Response(200, json={"response": "test successful"}),
)
async def test_send_request(ehr_client):
    ehr_client.request_data = [Mock(model_dump_json=Mock(return_value="{}"))]
    responses = await ehr_client.send_request("http://fakeurl.com")
    assert all(response["status"] == "success" for response in responses)


@pytest.mark.asyncio
async def test_logging_on_send_request_error(caplog, ehr_client):
    with patch.object(httpx.AsyncClient, "post") as mock_post:
        mock_post.return_value = Mock()
        mock_post.return_value.response.status_code = 400
        mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=Mock(url="http://fakeurl.com"),
            response=Mock(status_code="400"),
        )
        ehr_client.request_data = [
            Mock(model_dump_json=Mock(return_value="{'request': 'success'}"))
        ]
        responses = await ehr_client.send_request("http://fakeurl.com")
        assert "Error response 400 while requesting 'http://fakeurl.com" in caplog.text
        assert {} in responses
