import pytest
from healthchain.models.data.concept import Quantity
from pydantic import ValidationError


# Valid Cases
def test_valid():
    valid_floats = [1.0, 0.1, 4.5, 5.99999, 12455.321, 33, 1234, None]
    for num in valid_floats:
        q = Quantity(value=num, unit="mg")
        assert q.value == num


def test_valid_string():
    valid_strings = ["100", "100.000001", ".1", "1.", ".123", "1234.", "123989"]
    for string in valid_strings:
        q = Quantity(value=string, unit="mg")
        assert q.value == float(string)


# Invalid Cases
def test_invalid_strings():
    invalid_strings = [
        "1.0.0",
        "1..123",
        "..123",
        "12..",
        "12a.56",
        "1e4.6",
        "12#.45",
        "12.12@3",
        "12@3",
        "abc",
        "None",
        "",
    ]
    for string in invalid_strings:
        with pytest.raises(ValidationError) as exception_info:
            Quantity(value=string, unit="mg")
        assert "Invalid value" in str(exception_info.value)
