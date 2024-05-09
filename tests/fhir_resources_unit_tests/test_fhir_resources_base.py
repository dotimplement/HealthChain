from pydantic import ValidationError
import pytest
from pydantic import BaseModel
from healthchain.fhir_resources.base_resources import booleanModel, canonicalModel, codeModel


class booleanTestModel(BaseModel):
    my_bool: booleanModel

def test_boolean_valid():
    data = {"my_bool": "true"}
    result = booleanTestModel(**data)
    assert result.my_bool == "true"

def test_boolean_invalid():
    data = {"my_bool": "invalid"}
    with pytest.raises(ValidationError):
        booleanTestModel(**data)

class canonicalTestModel(BaseModel):
    my_canonical: canonicalModel

def test_canonical_valid():
    data = {"my_canonical": "https://example.com"}
    result = canonicalTestModel(**data)
    assert result.my_canonical == "https://example.com"

def test_canonical_invalid():
    data = {"my_canonical": "invalid url"}
    with pytest.raises(ValidationError):
        canonicalTestModel(**data)

class codeTestModel(BaseModel):
    my_code: codeModel

def test_code_valid():
    data = {"my_code": "ABC123"}
    result = codeTestModel(**data)
    assert result.my_code == "ABC123"

def test_code_invalid():
    data = {"my_code": "invalid     code"}
    with pytest.raises(ValidationError):
        codeTestModel(**data)

# Run the tests
if __name__ == "__main__":
    pytest.main()