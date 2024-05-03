import pytest

from unittest.mock import Mock
from healthchain.decorators import ehr


class MockUseCase:
    pass


class ClinicalDocumentation:
    construct_request = Mock(return_value=Mock(model_dump_json=Mock(return_value="{}")))


class ClinicalDecisionSupport:
    construct_request = Mock(return_value=Mock(model_dump_json=Mock(return_value="{}")))


@pytest.fixture
def function():
    def func(self):
        pass

    return func


class TestEHRDecorator:
    def test_use_case_not_configured(self, function):
        instance = MockUseCase()
        decorated = ehr(workflow="any_workflow")(function)
        with pytest.raises(ValueError) as excinfo:
            decorated(instance)
        assert "Use case not configured" in str(excinfo.value)

    def test_invalid_workflow(self, function):
        instance = ClinicalDocumentation()
        instance.use_case = ClinicalDocumentation()
        with pytest.raises(ValueError) as excinfo:
            decorated = ehr(workflow="invalid_workflow")(function)
            decorated(instance)
        assert "please select from" in str(excinfo.value)

    def test_unsupported_use_case(self, function):
        instance = MockUseCase()
        instance.use_case = MockUseCase()  # This use case should not be supported
        decorated = ehr(workflow="patient-view")(function)
        with pytest.raises(NotImplementedError):
            decorated(instance)

    def test_correct_behavior(self, function):
        instance = ClinicalDocumentation()
        instance.use_case = ClinicalDocumentation()
        decorated = ehr(workflow="order-sign")(function)
        result = decorated(instance)
        assert len(result.request_data) == 1

    def test_multiple_calls(self, function):
        instance = ClinicalDecisionSupport()
        instance.use_case = ClinicalDecisionSupport()
        decorated = ehr(workflow="order-select", num=3)(function)
        result = decorated(instance)
        assert len(result.request_data) == 3
