import pytest
from pydantic import ValidationError
from healthchain.config.validators import (
    ProblemSectionTemplateConfig,
    validate_document_config_model,
    register_template_config_model,
    TEMPLATE_CONFIG_REGISTRY,
    SECTION_VALIDATORS,
    AllergySectionTemplateConfig,
)


class TestCustomValidations:
    """Test domain-specific validation logic"""

    def test_custom_field_validators(self):
        """Test custom field validators in template models"""
        # Test problem_obs validator in ConditionTemplateConfig
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

        # Test allergy_obs validator in AllergyTemplateConfig
        invalid_allergy = {
            "act": {"template_id": "2.16.840.1.113883.10.20.22.4.30"},
            "allergy_obs": {
                "template_id": "2.16.840.1.113883.10.20.22.4.7",
                # Missing required fields
            },
            "clinical_status_obs": {
                "template_id": "2.16.840.1.113883.10.20.22.4.28",
                "code": "789012",
                "code_system": "2.16.840.1.113883.6.1",
                "status_code": "active",
            },
        }
        with pytest.raises(ValidationError) as excinfo:
            AllergySectionTemplateConfig(**invalid_allergy)

        assert "allergy_obs" in str(excinfo.value)


class TestPublicAPI:
    """Minimal tests for public API functions"""

    def test_document_validation(self):
        """Test document validation function with simple example"""
        # Missing required field in document config
        invalid_document = {
            "type_id": {"root": "2.16.840.1.113883.10.20.22.1.2"},
            "confidentiality_code": {"code": "N"},
            # Missing code field
        }
        assert validate_document_config_model("ccd", invalid_document) is False

    def test_registration_functions(self):
        """Verify registration functions add models to registries"""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            test_field: str

        # Record original state
        orig_count = len(TEMPLATE_CONFIG_REGISTRY)

        # Register model
        register_template_config_model("TestResource", TestModel)

        # Verify registration
        assert len(TEMPLATE_CONFIG_REGISTRY) == orig_count + 1
        assert "TestResource" in TEMPLATE_CONFIG_REGISTRY
        assert "TestResource" in SECTION_VALIDATORS

        # Clean up
        TEMPLATE_CONFIG_REGISTRY.pop("TestResource")
        SECTION_VALIDATORS.pop("TestResource")
