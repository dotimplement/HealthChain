import pytest

from healthchain.sandbox.decorator import sandbox


def test_sandbox_init(correct_sandbox_class):
    test_sandbox = correct_sandbox_class()
    attributes = dir(test_sandbox)

    assert "cds_discovery" in attributes
    assert "cds_service" in attributes
    assert "service_config" in attributes
    assert "start_sandbox" in attributes
    assert "_service" in attributes
    assert "_service_api" in attributes
    assert "_client" in attributes

    assert test_sandbox._service_api == "bar"
    assert test_sandbox._client == "foo"

    print(test_sandbox._service)

    assert test_sandbox._service is not None
    assert test_sandbox._service.endpoints.get("info").path == "/cds-services"
    assert (
        test_sandbox._service.endpoints.get("service_mount").path
        == "/cds-services/{id}"
    )


def test_sandbox_init_with_args(correct_sandbox_class_with_args):
    test_sandbox = correct_sandbox_class_with_args()

    assert test_sandbox.service_config == {
        "host": "123.0.0.1",
        "port": 9000,
        "ssl_keyfile": "foo",
    }


def test_sandbox_init_with_incorrect_args(correct_sandbox_class_with_incorrect_args):
    test_sandbox = correct_sandbox_class_with_incorrect_args()

    assert test_sandbox.service_config == {}


def test_incorrect_sandbox_usage(
    incorrect_api_num_sandbox_class,
    incorrect_client_num_sandbox_class,
    missing_funcs_sandbox_class,
):
    with pytest.raises(
        RuntimeError,
        match="Multiple methods are registered as _service_api. Only one is allowed.",
    ):
        incorrect_api_num_sandbox_class()

    with pytest.raises(
        RuntimeError,
        match="Multiple methods are registered as _client. Only one is allowed.",
    ):
        incorrect_client_num_sandbox_class()

    with pytest.raises(
        RuntimeError,
        match="Service API or Client is not configured. Please check your class initialization.",
    ):
        incorrect_class = missing_funcs_sandbox_class()
        incorrect_class.start_sandbox()

    with pytest.raises(
        TypeError,
        match="The 'sandbox' decorator can only be applied to subclasses of BaseUseCase, got testSandbox",
    ):

        class testSandbox:
            pass

        sandbox(testSandbox)


# TODO: write test for the start_sandbox func
