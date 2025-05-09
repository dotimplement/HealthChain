import pytest

from unittest.mock import patch, MagicMock

from healthchain.sandbox.decorator import sandbox
from healthchain.sandbox.environment import SandboxEnvironment
from healthchain.sandbox.workflows import UseCaseType


def test_sandbox_init(correct_sandbox_class):
    test_sandbox = correct_sandbox_class()
    attributes = dir(test_sandbox)

    # Check that required attributes are present
    assert "start_sandbox" in attributes
    assert "stop_sandbox" in attributes
    assert "_client" in attributes
    assert "sandbox_env" in attributes

    # Check client is correctly initialized
    assert test_sandbox._client == "foo"


def test_incorrect_sandbox_usage(
    incorrect_client_num_sandbox_class,
    missing_funcs_sandbox_class,
):
    # Test multiple client methods
    with pytest.raises(
        RuntimeError,
        match="Multiple methods are registered as _client. Only one is allowed.",
    ):
        incorrect_client_num_sandbox_class()

    # Test when no client is configured
    with pytest.raises(
        RuntimeError,
        match="Client is not configured. Please check your class initialization.",
    ):
        incorrect_class = missing_funcs_sandbox_class()
        incorrect_class.start_sandbox()

    # Test when decorator is applied to non-BaseUseCase class
    with pytest.raises(
        TypeError,
        match="The 'sandbox' decorator can only be applied to subclasses of BaseUseCase, got testSandbox",
    ):

        @sandbox("http://localhost:8000")
        class testSandbox:
            pass

        sandbox(testSandbox)


def test_start_sandbox(correct_sandbox_class):
    """Test the start_sandbox function"""
    test_sandbox = correct_sandbox_class()

    # Mock SandboxEnvironment to prevent actual execution
    mock_env = MagicMock()
    test_sandbox.sandbox_env = mock_env

    # Test with default parameters
    test_sandbox.start_sandbox()
    mock_env.start_sandbox.assert_called_once_with(
        service_id=None, save_data=True, save_dir="./output/", logging_config=None
    )

    # Reset mock and test with custom parameters
    mock_env.reset_mock()
    service_id = "test-service"
    save_dir = "./custom_dir/"
    logging_config = {"level": "DEBUG"}

    test_sandbox.start_sandbox(
        service_id=service_id,
        save_data=False,
        save_dir=save_dir,
        logging_config=logging_config,
    )

    mock_env.start_sandbox.assert_called_once_with(
        service_id=service_id,
        save_data=False,
        save_dir=save_dir,
        logging_config=logging_config,
    )


def test_sandbox_environment_init():
    """Test SandboxEnvironment initialization"""
    api = "http://localhost:8000"
    path = "/test"
    client = MagicMock()
    use_case_type = UseCaseType.cds
    config = {"test": "config"}

    env = SandboxEnvironment(api, path, client, use_case_type, config)

    assert env._client == client
    assert env.type == use_case_type
    assert str(env.api) == api
    assert env.path == path
    assert env.config == config
    assert env.responses == []
    assert env.sandbox_id is None


@patch("uuid.uuid4")
@patch("asyncio.run")
@patch("healthchain.sandbox.environment.ensure_directory_exists")
@patch("healthchain.sandbox.environment.save_data_to_directory")
def test_sandbox_environment_start_sandbox(
    mock_save_data, mock_ensure_dir, mock_asyncio_run, mock_uuid
):
    """Test SandboxEnvironment.start_sandbox"""
    # Setup mocks
    mock_uuid.return_value = "test-uuid"
    mock_asyncio_run.return_value = ["response1", "response2"]
    mock_ensure_dir.return_value = "/test/path"

    # Setup environment
    client = MagicMock()
    client.request_data = [MagicMock(), MagicMock()]
    client.request_data[0].model_dump.return_value = {"request": "data1"}
    client.request_data[1].model_dump.return_value = {"request": "data2"}

    env = SandboxEnvironment(
        "http://localhost:8000", "/test", client, UseCaseType.cds, {}
    )

    # Test start_sandbox
    env.start_sandbox(service_id="test-service", save_data=True)

    # Verify method calls
    mock_uuid.assert_called_once()
    mock_asyncio_run.assert_called_once()
    assert env.sandbox_id == "test-uuid"
    assert env.responses == ["response1", "response2"]

    # For CDS (JSON), we should call model_dump
    assert mock_save_data.call_count == 2
