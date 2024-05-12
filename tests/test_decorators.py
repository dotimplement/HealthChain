import pytest

from unittest.mock import Mock
from healthchain.decorators import ehr
from healthchain.base import BaseUseCase, UseCaseType


class MockUseCase:
    pass


class MockClinicalDocumentation(BaseUseCase):
    def _validate_data(self):
        pass

    construct_request = Mock(return_value=Mock(model_dump_json=Mock(return_value="{}")))
    type = UseCaseType.clindoc


class MockClinicalDecisionSupport(BaseUseCase):
    def _validate_data(self):
        pass

    construct_request = Mock(return_value=Mock(model_dump_json=Mock(return_value="{}")))
    type = UseCaseType.cds


@pytest.fixture
def function():
    def func(self):
        pass

    return func


class TestEHRDecorator:
    def test_invalid_use_case(self, function):
        instance = MockUseCase()
        decorated = ehr(workflow="any_workflow")(function)
        with pytest.raises(AssertionError) as excinfo:
            decorated(instance)
        assert "MockUseCase must be subclass of valid Use Case strategy!" in str(
            excinfo.value
        )

    def test_invalid_workflow(self, function):
        instance = MockClinicalDocumentation()
        instance.use_case = MockClinicalDocumentation()
        with pytest.raises(ValueError) as excinfo:
            decorated = ehr(workflow="invalid_workflow")(function)
            decorated(instance)
        assert "please select from" in str(excinfo.value)

    def test_correct_behavior(self, function):
        instance = MockClinicalDecisionSupport()
        instance.use_case = MockClinicalDecisionSupport()
        decorated = ehr(workflow="order-sign")(function)
        result = decorated(instance)
        assert len(result.request_data) == 1

    def test_multiple_calls(self, function):
        instance = MockClinicalDecisionSupport()
        instance.use_case = MockClinicalDecisionSupport()
        decorated = ehr(workflow="order-select", num=3)(function)
        result = decorated(instance)
        assert len(result.request_data) == 3
