from pydantic import ValidationError
import pytest
from src.pydantic_models import booleanModel, canonicalModel, codeModel

def test_boolean_valid():
    data = {"boolean": "true"}
    result = booleanModel(**data)
    assert result.boolean == "true"

def test_boolean_invalid():
    data = {"boolean": "invalid"}
    with pytest.raises(ValidationError):
        booleanModel(**data)

def test_canonical_valid():
    data = {"canonical": "https://example.com"}
    result = canonicalModel(**data)
    assert result.canonical == "https://example.com"

def test_canonical_invalid():
    data = {"canonical": "invalid url"}
    with pytest.raises(ValidationError):
        canonicalModel(**data)

def test_code_valid():
    data = {"code": "ABC123"}
    result = codeModel(**data)
    assert result.code == "ABC123"

def test_code_invalid():
    data = {"code": "invalid     code"}
    with pytest.raises(ValidationError):
        codeModel(**data)

# Run the tests
if __name__ == "__main__":
    pytest.main()