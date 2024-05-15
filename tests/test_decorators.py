import pytest

from healthchain.decorators import ehr


class MockUseCase:
    pass


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
