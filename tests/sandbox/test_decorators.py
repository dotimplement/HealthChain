import pytest
from unittest.mock import MagicMock

from healthchain.sandbox.decorator import ehr
from healthchain.sandbox.utils import find_attributes_of_type, assign_to_attribute
from healthchain.sandbox.workflows import UseCaseType
from healthchain.sandbox.base import BaseUseCase

from .conftest import MockDataGenerator


class MockUseCase:
    def __init__(self) -> None:
        self.data_gen = MockDataGenerator()


@pytest.fixture
def function():
    def func(self):
        pass

    return func


def test_setting_workflow_attributes():
    instance = MockUseCase()
    attributes = find_attributes_of_type(instance, MockDataGenerator)
    assert attributes == ["data_gen"]


def test_assigning_workflow_attributes():
    instance = MockUseCase()
    attributes = ["data_gen", "invalid"]

    assign_to_attribute(instance, attributes[0], "set_workflow", "workflow")
    assert instance.data_gen.workflow == "workflow"

    with pytest.raises(AttributeError):
        assign_to_attribute(instance, attributes[1], "set_workflow", "workflow")


def test_ehr_invalid_use_case(function):
    instance = MockUseCase()
    decorated = ehr(workflow="any_workflow")(function)
    with pytest.raises(AssertionError) as excinfo:
        decorated(instance)
    assert "MockUseCase must be subclass of valid Use Case strategy!" in str(
        excinfo.value
    )


def test_ehr_invalid_workflow(function, mock_cds):
    with pytest.raises(ValueError) as excinfo:
        decorated = ehr(workflow="invalid_workflow")(function)
        decorated(mock_cds())
    assert "please select from" in str(excinfo.value)


def test_ehr_correct_behavior(function, mock_cds):
    decorated = ehr(workflow="order-sign")(function)
    result = decorated(mock_cds())
    assert len(result.request_data) == 1


def test_ehr_multiple_calls(function, mock_cds):
    decorated = ehr(workflow="order-select", num=3)(function)
    result = decorated(mock_cds())
    assert len(result.request_data) == 3


def test_ehr_decorator():
    """Test the ehr decorator functionality"""

    # Create a proper subclass of BaseUseCase to avoid patching
    class MockUseCase(BaseUseCase):
        type = UseCaseType.cds
        path = "/test"

        # Mock strategy for testing
        @property
        def strategy(self):
            return MagicMock()

        # Test the decorator with workflow
        @ehr(workflow="patient-view")
        def test_method(self):
            return {"test": "data"}

    # Create an instance
    mock_use_case = MockUseCase()

    # Verify method is marked as client
    assert hasattr(mock_use_case.test_method, "is_client")
    assert mock_use_case.test_method.is_client
