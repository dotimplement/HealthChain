import dataclasses
import pytest

from unittest.mock import Mock
from pydantic import BaseModel

from healthchain.base import BaseStrategy, BaseUseCase, UseCaseType
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.use_cases.cds import ClinicalDecisionSupportStrategy
from healthchain.clients import EHRClient
from healthchain.decorators import sandbox
from healthchain.use_cases.cds import ClinicalDecisionSupport


class MockBundle(BaseModel):
    condition: str = "test"


# TEMP
@dataclasses.dataclass
class synth_data:
    context: dict
    resources: MockBundle


class MockDataGenerator:
    def __init__(self) -> None:
        self.data = synth_data(context={}, resources=MockBundle())
        self.workflow = None

    def set_workflow(self, workflow):
        self.workflow = workflow


@pytest.fixture
def cds_strategy():
    return ClinicalDecisionSupportStrategy()


@pytest.fixture
def valid_data():
    return synth_data(
        context={"userId": "Practitioner/123", "patientId": "123"},
        resources=MockBundle(),
    )


@pytest.fixture
def invalid_data():
    return synth_data(
        context={"invalidId": "Practitioner", "patientId": "123"},
        resources=MockBundle(),
    )


@pytest.fixture
def mock_function():
    return Mock()


@pytest.fixture
def mock_workflow():
    return Mock()


@pytest.fixture
def mock_strategy():
    mock = Mock()
    mock.construct_request = Mock(
        return_value=Mock(model_dump_json=Mock(return_value="{}"))
    )
    return mock


@pytest.fixture
def ehr_client(mock_function, mock_workflow, mock_strategy):
    return EHRClient(mock_function, mock_workflow, mock_strategy)


@pytest.fixture(scope="function")
def mock_cds_strategy() -> BaseStrategy:
    class MockClinicalDecisionSupportStrategy(BaseStrategy):
        def _validate_data(self):
            pass

        construct_request = Mock(
            return_value=Mock(model_dump_json=Mock(return_value="{}"))
        )

    return MockClinicalDecisionSupportStrategy()


@pytest.fixture
def mock_cds() -> BaseUseCase:
    class MockClinicalDecisionSupportStrategy(BaseStrategy):
        def _validate_data(self):
            pass

        construct_request = Mock(
            return_value=Mock(model_dump_json=Mock(return_value="{}"))
        )

    class MockClinicalDecisionSupport(BaseUseCase):
        type = UseCaseType.cds
        endpoints = {}
        strategy = MockClinicalDecisionSupportStrategy()

    return MockClinicalDecisionSupport


@pytest.fixture
def test_cds_request():
    cds_dict = {
        "hook": "patient-view",
        "hookInstance": "29e93987-c345-4cb7-9a92-b5136289c2a4",
        "context": {"userId": "Practitioner/123", "patientId": "123"},
    }
    return CDSRequest(**cds_dict)


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
        def foo(self):
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
        def foo(self):
            return "foo"

        @mock_client_decorator
        def foo2(self):
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
        def foo(self):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

        @mock_api_decorator
        def bar2(self):
            return "bar"

    return testSandbox


@pytest.fixture
def correct_sandbox_class_with_args(mock_api_decorator, mock_client_decorator):
    @sandbox(service_config={"host": "123.0.0.1", "port": 9000, "ssl_keyfile": "foo"})
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

    return testSandbox


@pytest.fixture
def correct_sandbox_class_with_incorrect_args(
    mock_api_decorator, mock_client_decorator
):
    @sandbox(incorrect_arg={"something": 8000})
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self):
            return "foo"

        @mock_api_decorator
        def bar(self):
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


@pytest.fixture
def cds():
    service_api_mock = Mock()
    service_config = {"host": "localhost", "port": 8080}
    service_mock = Mock()
    client_mock = Mock()
    client_mock.workflow.value = "hook1"
    return ClinicalDecisionSupport(
        service_api=service_api_mock,
        service_config=service_config,
        service=service_mock,
        client=client_mock,
    )
