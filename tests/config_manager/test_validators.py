import pytest
from pydantic import ValidationError
from healthchain.config.validators import (
    ProblemSectionTemplateConfig,
    validate_cda_document_config_model,
    register_cda_section_template_config_model,
    CDA_SECTION_CONFIG_REGISTRY,
    SECTION_VALIDATORS,
)


def test_custom_field_validation():
    """Test critical domain-specific validation logic"""
    # Test problem_obs validator in ProblemSectionTemplateConfig
    invalid_condition = {
        "act": {"template_id": "2.16.840.1.113883.10.20.22.4.3"},
        "problem_obs": {
            "template_id": "2.16.840.1.113883.10.20.22.4.4",
            # Missing required fields
        },
        "clinical_status_obs": {
            "template_id": "2.16.840.1.113883.10.20.22.4.5",
            "code": "789012",
            "code_system": "2.16.840.1.113883.6.1",
            "status_code": "active",
        },
    }
    with pytest.raises(ValidationError) as excinfo:
        ProblemSectionTemplateConfig(**invalid_condition)

    # Verify the specific validation error relates to our custom validator
    assert "problem_obs" in str(excinfo.value)


def test_core_functionality():
    """Test essential public API functions"""
    # Test document validation
    invalid_document = {
        "type_id": {"root": "2.16.840.1.113883.10.20.22.1.2"},
        "confidentiality_code": {"code": "N"},
        # Missing code field
    }
    assert validate_cda_document_config_model("ccd", invalid_document) is False

    # Test template registration
    from pydantic import BaseModel

    class TestModel(BaseModel):
        test_field: str

    # Record original state and register model
    register_cda_section_template_config_model("TestResource", TestModel)

    # Verify registration
    assert "TestResource" in CDA_SECTION_CONFIG_REGISTRY
    assert "TestResource" in SECTION_VALIDATORS

    # Clean up
    CDA_SECTION_CONFIG_REGISTRY.pop("TestResource")
    SECTION_VALIDATORS.pop("TestResource")
