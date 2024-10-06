import pytest 
from healthchain.models.data.concept import Quantity
from pydantic import ValidationError
#Valid Cases
def test_valid_float_and_integer():
    valid_floats = [1.0, .1, 4., 5.99999, 12455.321, 33, 1234]
    for num in valid_floats : 
        q = Quantity(value  = num,unit = "mg");
        assert q.value == num

def test_valid_string():
    valid_strings = ["100","100.000001",".1","1.",".123","1234.","123989"]
    for string in valid_strings:
        q = Quantity(value = string,unit = "mg");
        assert q.value == float(string)

# Invalid Cases
def test_invalid_strings():
    invalid_strings = ["1.0.0", "1..123", "..123","12..","12a.56","1e4.6","12#.45","12.12@3","12@3"]
    for string in invalid_strings:
        with pytest.raises(ValidationError) as exception_info:
            q = Quantity(value = string,unit = "mg")
        assert "Invalid value" in str(exception_info.value)
        

#Edge Cases
def test_edge_cases():
    
    edge_cases = ["", "None", None]
    for val in edge_cases:
        with pytest.raises((ValidationError,TypeError)) as exception_info:
            q = Quantity(value = val,unit = "mg")
    
        exception_info_str = str(exception_info.value)
        assert any(msg in exception_info_str for msg in ["CANNOT", "Invalid value"])

# if __name__ == '__main__':
#     q = Quantity("12","mg");
#     print(q);