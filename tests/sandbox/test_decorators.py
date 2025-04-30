import pytest

from healthchain.sandbox.decorator import api, ehr
from healthchain.sandbox.utils import find_attributes_of_type, assign_to_attribute
from healthchain.sandbox.apimethod import APIMethod

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


class TestEHRDecorator:
    def test_invalid_use_case(self, function):
        instance = MockUseCase()
        decorated = ehr(workflow="any_workflow")(function)
        with pytest.raises(AssertionError) as excinfo:
            decorated(instance)
        assert "MockUseCase must be subclass of valid Use Case strategy!" in str(
            excinfo.value
        )

    def test_invalid_workflow(self, function, mock_cds):
        with pytest.raises(ValueError) as excinfo:
            decorated = ehr(workflow="invalid_workflow")(function)
            decorated(mock_cds())
        assert "please select from" in str(excinfo.value)

    def test_correct_behavior(self, function, mock_cds):
        decorated = ehr(workflow="order-sign")(function)
        result = decorated(mock_cds())
        assert len(result.request_data) == 1

    def test_multiple_calls(self, function, mock_cds):
        decorated = ehr(workflow="order-select", num=3)(function)
        result = decorated(mock_cds())
        assert len(result.request_data) == 3


# TODO: add test for api decorator
def test_api_decorator():
    @api
    def test_function():
        return "test"

    # test if the function is correctly wrapped in the APImethod instance.
    result = test_function()
    assert isinstance(result, APIMethod)
    assert result.func() == "test"

    # test if function has "is_service_route"
    assert hasattr(test_function, "is_service_route")

    # test if the "is_service_route" member is set to True.
    assert test_function.is_service_route is True
