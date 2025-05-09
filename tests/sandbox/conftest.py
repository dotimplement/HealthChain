import pytest

from unittest.mock import Mock
from healthchain.fhir import create_bundle
from healthchain.models.hooks.prefetch import Prefetch
from healthchain.sandbox.base import BaseRequestConstructor, BaseUseCase
from healthchain.sandbox.clients import EHRClient
from healthchain.sandbox.decorator import sandbox
from healthchain.sandbox.use_cases.cds import ClinicalDecisionSupport
from healthchain.sandbox.workflows import UseCaseType


class MockDataGenerator:
    def __init__(self) -> None:
        self.generated_data = Prefetch(prefetch={"document": create_bundle()})
        self.workflow = None

    def set_workflow(self, workflow):
        self.workflow = workflow


@pytest.fixture
def mock_strategy():
    mock = Mock()
    mock.construct_request = Mock(
        return_value=Mock(model_dump_json=Mock(return_value="{}"))
    )
    return mock


@pytest.fixture
def mock_function():
    return Mock()


@pytest.fixture
def mock_workflow():
    return Mock()


@pytest.fixture
def ehr_client(mock_function, mock_workflow, mock_strategy):
    return EHRClient(mock_function, mock_workflow, mock_strategy)


@pytest.fixture
def mock_cds() -> BaseUseCase:
    class MockClinicalDecisionSupportStrategy(BaseRequestConstructor):
        # Add required api_protocol property
        api_protocol = "rest"

        construct_request = Mock(
            return_value=Mock(model_dump_json=Mock(return_value="{}"))
        )

    class MockClinicalDecisionSupport(BaseUseCase):
        type = UseCaseType.cds
        _path = "/cds"
        strategy = MockClinicalDecisionSupportStrategy()

        @property
        def path(self):
            return self._path

    return MockClinicalDecisionSupport


@pytest.fixture
def mock_client_decorator():
    """Create a mock decorator for client methods"""

    def mock_client_decorator(func):
        func.is_client = True
        return func

    return mock_client_decorator


@pytest.fixture
def correct_sandbox_class(mock_client_decorator):
    """Create a correct sandbox class with required API URL"""

    @sandbox("http://localhost:8000")
    class TestSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            super().__init__(path="/cds-services/")

        @mock_client_decorator
        def foo(self):
            return "foo"

    return TestSandbox


@pytest.fixture
def incorrect_client_num_sandbox_class(mock_client_decorator):
    """Create a sandbox class with too many client methods"""

    @sandbox("http://localhost:8000")
    class TestSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            super().__init__(path="/cds-services/")

        @mock_client_decorator
        def foo(self):
            return "foo"

        @mock_client_decorator
        def foo2(self):
            return "foo"

    return TestSandbox


@pytest.fixture
def missing_funcs_sandbox_class():
    """Create a sandbox class with missing client methods"""

    @sandbox("http://localhost:8000")
    class TestSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            super().__init__(path="/cds-services/")

    return TestSandbox
