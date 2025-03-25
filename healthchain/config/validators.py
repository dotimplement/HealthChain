"""
Configuration validators for HealthChain

This module provides validation models and utilities for configuration files.
"""

import logging
from pydantic import BaseModel, ValidationError, field_validator
from typing import Dict, List, Any, Optional, Type, Union

logger = logging.getLogger(__name__)

#
# Base Models
#


class ComponentTemplateConfig(BaseModel):
    """Generic template for CDA/FHIR component configuration"""

    template_id: Union[List[str], str]
    code: Optional[str] = None
    code_system: Optional[str] = "2.16.840.1.113883.6.1"
    code_system_name: Optional[str] = "LOINC"
    display_name: Optional[str] = None
    status_code: Optional[str] = "active"
    class_code: Optional[str] = None
    mood_code: Optional[str] = None
    type_code: Optional[str] = None
    inversion_ind: Optional[bool] = None
    value: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class SectionIdentifiersConfig(BaseModel):
    """Section identifiers validation"""

    template_id: str
    code: str
    code_system: Optional[str] = "2.16.840.1.113883.6.1"
    code_system_name: Optional[str] = "LOINC"
    display: str
    clinical_status: Optional[Dict[str, str]] = None
    reaction: Optional[Dict[str, str]] = None
    severity: Optional[Dict[str, str]] = None

    class Config:
        extra = "allow"


class RenderingConfig(BaseModel):
    """Configuration for section rendering"""

    narrative: Optional[Dict[str, Any]] = None
    entry: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class SectionBaseConfig(BaseModel):
    """Base model for all section configurations"""

    resource: str
    resource_template: str
    entry_template: str
    identifiers: SectionIdentifiersConfig
    rendering: Optional[RenderingConfig] = None

    class Config:
        extra = "allow"


#
# Resource-Specific Template Models
#


class ConditionTemplateConfig(BaseModel):
    """Template configuration for Condition resource"""

    act: ComponentTemplateConfig
    problem_obs: ComponentTemplateConfig
    clinical_status_obs: ComponentTemplateConfig

    @field_validator("problem_obs")
    @classmethod
    def validate_problem_obs(cls, v):
        required_fields = {"code", "code_system", "status_code"}
        missing = required_fields - set(v.model_dump(exclude_unset=True).keys())
        if missing:
            raise ValueError(f"problem_obs missing required fields: {missing}")
        return v

    @field_validator("clinical_status_obs")
    @classmethod
    def validate_clinical_status(cls, v):
        required_fields = {"code", "code_system", "status_code"}
        missing = required_fields - set(v.model_dump(exclude_unset=True).keys())
        if missing:
            raise ValueError(f"clinical_status_obs missing required fields: {missing}")
        return v


class MedicationTemplateConfig(BaseModel):
    """Template configuration for MedicationStatement resource"""

    substance_admin: ComponentTemplateConfig
    manufactured_product: ComponentTemplateConfig
    clinical_status_obs: ComponentTemplateConfig

    @field_validator("substance_admin")
    @classmethod
    def validate_substance_admin(cls, v):
        if not v.status_code:
            raise ValueError("substance_admin requires status_code")
        return v


class AllergyTemplateConfig(BaseModel):
    """Template configuration for AllergyIntolerance resource"""

    act: ComponentTemplateConfig
    allergy_obs: ComponentTemplateConfig
    reaction_obs: Optional[ComponentTemplateConfig] = None
    severity_obs: Optional[ComponentTemplateConfig] = None
    clinical_status_obs: ComponentTemplateConfig

    @field_validator("allergy_obs")
    @classmethod
    def validate_allergy_obs(cls, v):
        required_fields = {"code", "code_system", "status_code"}
        missing = required_fields - set(v.model_dump(exclude_unset=True).keys())
        if missing:
            raise ValueError(f"allergy_obs missing required fields: {missing}")
        return v


class DocumentConfig(BaseModel):
    """Generic document configuration model"""

    type_id: Dict[str, Any]
    code: Dict[str, Any]
    confidentiality_code: Dict[str, Any]
    language_code: Optional[str] = "en-US"
    templates: Optional[Dict[str, Any]] = None
    structure: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    rendering: Optional[Dict[str, Any]] = None

    @field_validator("type_id")
    @classmethod
    def validate_type_id(cls, v):
        if not isinstance(v, dict) or "root" not in v:
            raise ValueError("type_id must contain 'root' field")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        if not isinstance(v, dict) or "code" not in v or "code_system" not in v:
            raise ValueError("code must contain 'code' and 'code_system' fields")
        return v

    @field_validator("confidentiality_code")
    @classmethod
    def validate_confidentiality_code(cls, v):
        if not isinstance(v, dict) or "code" not in v:
            raise ValueError("confidentiality_code must contain 'code' field")
        return v

    class Config:
        extra = "allow"


#
# Registries and Factory Functions
#

TEMPLATE_REGISTRY = {
    "Condition": ConditionTemplateConfig,
    "MedicationStatement": MedicationTemplateConfig,
    "AllergyIntolerance": AllergyTemplateConfig,
}

DOCUMENT_REGISTRY = {
    "ccd": DocumentConfig,
}


def create_section_validator(
    resource_type: str, template_model: Type[BaseModel]
) -> Type[BaseModel]:
    """Create a section validator for a specific resource type"""

    class DynamicSectionConfig(SectionBaseConfig):
        template: Dict[str, Any]

        @field_validator("template")
        @classmethod
        def validate_template(cls, v):
            try:
                template_model(**v)
            except ValidationError as e:
                raise ValueError(f"Template validation failed: {str(e)}")
            return v

    DynamicSectionConfig.__name__ = f"{resource_type}SectionConfig"
    return DynamicSectionConfig


SECTION_VALIDATORS = {
    resource_type: create_section_validator(resource_type, template_model)
    for resource_type, template_model in TEMPLATE_REGISTRY.items()
}

#
# Validation Functions
#


def validate_section_config(section_key: str, section_config: Dict[str, Any]) -> bool:
    """Validate a section configuration"""
    resource_type = section_config.get("resource")
    if not resource_type:
        logger.error(f"Section '{section_key}' is missing 'resource' field")
        return False

    validator = SECTION_VALIDATORS.get(resource_type)
    if not validator:
        logger.warning(f"No specific validator for resource type: {resource_type}")
        return True

    try:
        validator(**section_config)
        return True
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            location = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"  - {location}: {message}")

        error_str = f"Validation failed for section '{section_key}':\n" + "\n".join(
            error_messages
        )
        logger.error(error_str)
        return False


def validate_document_config(
    document_type: str, document_config: Dict[str, Any]
) -> bool:
    """Validate a document configuration"""
    validator = DOCUMENT_REGISTRY.get(document_type.lower(), DocumentConfig)

    try:
        validator(**document_config)
        return True
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            location = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"  - {location}: {message}")

        error_str = (
            f"Validation failed for document type '{document_type}':\n"
            + "\n".join(error_messages)
        )
        logger.error(error_str)
        return False


#
# Registration Functions
#


def register_template_model(
    resource_type: str, template_model: Type[BaseModel]
) -> None:
    """Register a custom template model for a resource type"""
    TEMPLATE_REGISTRY[resource_type] = template_model
    SECTION_VALIDATORS[resource_type] = create_section_validator(
        resource_type, template_model
    )
    logger.info(f"Registered custom template model for {resource_type}")


def register_document_model(
    document_type: str, document_model: Type[BaseModel]
) -> None:
    """Register a custom document model"""
    DOCUMENT_REGISTRY[document_type.lower()] = document_model
    logger.info(f"Registered custom document model for {document_type}")
