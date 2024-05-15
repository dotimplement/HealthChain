import pytest

from healthchain.decorators import sandbox
from healthchain.use_cases.cds import ClinicalDecisionSupport


@pytest.fixture
def mock_client_decorator():
    def mock_client_decorator(func):
        func.is_client = True
        return func

    return mock_client_decorator


@pytest.fixture
def mock_api_decorator():
    def mock_api_decorator(func):
        func.is_service_route = True
        return func

    return mock_api_decorator


@pytest.fixture
def correct_sandbox_class(mock_api_decorator, mock_client_decorator):
    @sandbox
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self, test):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

    return testSandbox


@pytest.fixture
def incorrect_client_num_sandbox_class(mock_api_decorator, mock_client_decorator):
    @sandbox
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self, test):
            return "foo"

        @mock_client_decorator
        def foo2(self, test):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

    return testSandbox


@pytest.fixture
def incorrect_api_num_sandbox_class(mock_api_decorator, mock_client_decorator):
    @sandbox
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self, test):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

        @mock_api_decorator
        def bar2(self):
            return "bar"

    return testSandbox


@pytest.fixture
def missing_funcs_sandbox_class():
    @sandbox
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

    return testSandbox


@pytest.fixture
def wrong_subclass_sandbox_class():
    @sandbox
    class testSandbox:
        def __init__(self) -> None:
            pass

    return testSandbox


def test_sandbox_init(correct_sandbox_class):
    test_sandbox = correct_sandbox_class()
    attributes = dir(test_sandbox)

    assert "cds_discovery" in attributes
    assert "cds_service" in attributes
    assert "service" in attributes
    assert "service_api" in attributes
    assert "client" in attributes
    assert "service_config" in attributes
    assert "start_sandbox" in attributes

    assert test_sandbox.service_api == "bar"
    assert test_sandbox.client == "foo"

    assert test_sandbox.service is not None
    assert test_sandbox.service.endpoints.get("info").path == "/cds-services"
    assert (
        test_sandbox.service.endpoints.get("service_mount").path == "/cds-services/{id}"
    )


def test_incorrect_sandbox_usage(
    incorrect_api_num_sandbox_class,
    incorrect_client_num_sandbox_class,
    missing_funcs_sandbox_class,
):
    with pytest.raises(
        RuntimeError,
        match="Multiple methods are registered as service api. Only one is allowed.",
    ):
        incorrect_api_num_sandbox_class()

    with pytest.raises(
        RuntimeError,
        match="Multiple methods are registered as client. Only one is allowed.",
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
# TODO: write test for sandbox decorator with input args
