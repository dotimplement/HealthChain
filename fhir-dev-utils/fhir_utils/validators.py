"""
FHIR Resource Validation Helpers

Provides comprehensive validation utilities for FHIR resources
including schema validation, reference integrity, and custom rules.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union, Type, Set
from enum import Enum

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from pydantic import ValidationError


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: ValidationSeverity
    message: str
    path: Optional[str] = None
    rule: Optional[str] = None

    def __str__(self) -> str:
        location = f" at {self.path}" if self.path else ""
        return f"[{self.severity.value.upper()}]{location}: {self.message}"


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def error_count(self) -> int:
        """Count of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return len(self.warnings)

    def add_error(self, message: str, path: Optional[str] = None,
                  rule: Optional[str] = None) -> None:
        """Add an error issue."""
        self.issues.append(ValidationIssue(
            ValidationSeverity.ERROR, message, path, rule
        ))
        self.is_valid = False

    def add_warning(self, message: str, path: Optional[str] = None,
                    rule: Optional[str] = None) -> None:
        """Add a warning issue."""
        self.issues.append(ValidationIssue(
            ValidationSeverity.WARNING, message, path, rule
        ))

    def add_info(self, message: str, path: Optional[str] = None,
                 rule: Optional[str] = None) -> None:
        """Add an info issue."""
        self.issues.append(ValidationIssue(
            ValidationSeverity.INFO, message, path, rule
        ))

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one."""
        self.issues.extend(other.issues)
        if not other.is_valid:
            self.is_valid = False
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {
                    "severity": i.severity.value,
                    "message": i.message,
                    "path": i.path,
                    "rule": i.rule
                }
                for i in self.issues
            ]
        }

    def __str__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        lines = [f"Validation Result: {status}"]
        if self.resource_type:
            lines.append(f"Resource: {self.resource_type}/{self.resource_id or 'unknown'}")
        lines.append(f"Errors: {self.error_count}, Warnings: {self.warning_count}")
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


class FHIRValidator:
    """
    Comprehensive FHIR resource validator.

    Provides schema validation, reference integrity checks,
    and custom validation rules.
    """

    # Standard code systems for validation
    CODE_SYSTEMS = {
        "snomed": "http://snomed.info/sct",
        "loinc": "http://loinc.org",
        "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
        "icd10": "http://hl7.org/fhir/sid/icd-10-cm",
        "ucum": "http://unitsofmeasure.org",
    }

    # Required fields by resource type
    REQUIRED_FIELDS: Dict[str, List[str]] = {
        "Patient": [],
        "Condition": ["subject"],
        "Observation": ["status", "code"],
        "MedicationStatement": ["status", "subject", "medicationCodeableConcept"],
        "AllergyIntolerance": ["patient"],
        "Bundle": ["type"],
    }

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, warnings are treated as errors
        """
        self.strict = strict
        self._custom_rules: Dict[str, List[callable]] = {}

    def add_custom_rule(
        self,
        resource_type: str,
        rule_fn: callable,
        rule_name: Optional[str] = None
    ) -> None:
        """
        Add a custom validation rule.

        Args:
            resource_type: Resource type to apply rule to
            rule_fn: Function(resource, result) that adds issues to result
            rule_name: Optional name for the rule
        """
        if resource_type not in self._custom_rules:
            self._custom_rules[resource_type] = []
        self._custom_rules[resource_type].append((rule_fn, rule_name))

    def validate(
        self,
        resource: Union[Resource, Dict[str, Any]],
        validate_references: bool = True,
        check_recommended: bool = True
    ) -> ValidationResult:
        """
        Validate a FHIR resource.

        Args:
            resource: FHIR resource or dict representation
            validate_references: Check reference format validity
            check_recommended: Check recommended fields

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(is_valid=True)

        # Convert dict to resource if needed
        if isinstance(resource, dict):
            try:
                resource_type = resource.get("resourceType")
                if not resource_type:
                    result.add_error("Missing resourceType field")
                    return result
                result.resource_type = resource_type
                result.resource_id = resource.get("id")

                # Try to parse as FHIR resource
                from fhir.resources import get_fhir_model_class
                model_class = get_fhir_model_class(resource_type)
                resource = model_class(**resource)
            except ValidationError as e:
                for error in e.errors():
                    path = ".".join(str(p) for p in error["loc"])
                    result.add_error(error["msg"], path=path, rule="schema")
                return result
            except Exception as e:
                result.add_error(f"Invalid resource: {str(e)}", rule="schema")
                return result
        else:
            result.resource_type = resource.resource_type
            result.resource_id = getattr(resource, "id", None)

        # Check required fields
        self._validate_required_fields(resource, result)

        # Validate references
        if validate_references:
            self._validate_references(resource, result)

        # Check recommended fields
        if check_recommended:
            self._check_recommended_fields(resource, result)

        # Run custom rules
        self._run_custom_rules(resource, result)

        # In strict mode, warnings become errors
        if self.strict:
            for issue in result.warnings:
                issue.severity = ValidationSeverity.ERROR
            if result.warnings:
                result.is_valid = False

        return result

    def _validate_required_fields(
        self,
        resource: Resource,
        result: ValidationResult
    ) -> None:
        """Check that required fields are present."""
        resource_type = resource.resource_type
        required = self.REQUIRED_FIELDS.get(resource_type, [])

        for field_name in required:
            value = getattr(resource, field_name, None)
            if value is None:
                result.add_error(
                    f"Required field '{field_name}' is missing",
                    path=field_name,
                    rule="required"
                )

    def _validate_references(
        self,
        resource: Resource,
        result: ValidationResult
    ) -> None:
        """Validate reference formats."""
        resource_dict = resource.model_dump(exclude_none=True)
        self._check_references_recursive(resource_dict, "", result)

    def _check_references_recursive(
        self,
        data: Any,
        path: str,
        result: ValidationResult
    ) -> None:
        """Recursively check references in nested data."""
        if isinstance(data, dict):
            if "reference" in data:
                ref_value = data["reference"]
                if not self._is_valid_reference(ref_value):
                    result.add_error(
                        f"Invalid reference format: {ref_value}",
                        path=f"{path}.reference" if path else "reference",
                        rule="reference-format"
                    )
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                self._check_references_recursive(value, new_path, result)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._check_references_recursive(item, f"{path}[{i}]", result)

    def _is_valid_reference(self, reference: str) -> bool:
        """Check if reference string is valid."""
        if not reference:
            return False

        # Check for valid formats: ResourceType/id, urn:uuid:..., or absolute URL
        patterns = [
            r"^[A-Z][a-zA-Z]+/[a-zA-Z0-9\-\.]+$",  # ResourceType/id
            r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            r"^https?://",  # Absolute URL
            r"^#",  # Contained reference
        ]
        return any(re.match(p, reference) for p in patterns)

    def _check_recommended_fields(
        self,
        resource: Resource,
        result: ValidationResult
    ) -> None:
        """Check for recommended but not required fields."""
        resource_type = resource.resource_type

        recommendations = {
            "Patient": [
                ("name", "Patient should have a name"),
                ("birthDate", "Patient should have a birth date"),
                ("gender", "Patient should have a gender"),
            ],
            "Condition": [
                ("code", "Condition should have a code"),
                ("clinicalStatus", "Condition should have clinical status"),
            ],
            "Observation": [
                ("subject", "Observation should reference a subject"),
                ("effectiveDateTime", "Observation should have an effective date"),
            ],
        }

        for field_name, message in recommendations.get(resource_type, []):
            value = getattr(resource, field_name, None)
            if value is None:
                result.add_warning(message, path=field_name, rule="recommended")

    def _run_custom_rules(
        self,
        resource: Resource,
        result: ValidationResult
    ) -> None:
        """Run any registered custom validation rules."""
        resource_type = resource.resource_type
        rules = self._custom_rules.get(resource_type, [])

        for rule_fn, rule_name in rules:
            try:
                rule_fn(resource, result)
            except Exception as e:
                result.add_error(
                    f"Custom rule failed: {str(e)}",
                    rule=rule_name or "custom"
                )


def validate_resource(
    resource: Union[Resource, Dict[str, Any]],
    strict: bool = False
) -> ValidationResult:
    """
    Convenience function to validate a single resource.

    Args:
        resource: FHIR resource to validate
        strict: Treat warnings as errors

    Returns:
        ValidationResult
    """
    validator = FHIRValidator(strict=strict)
    return validator.validate(resource)


def validate_bundle(
    bundle: Union[Bundle, Dict[str, Any]],
    strict: bool = False,
    validate_entry_resources: bool = True
) -> ValidationResult:
    """
    Validate a FHIR Bundle and optionally its entries.

    Args:
        bundle: Bundle to validate
        strict: Treat warnings as errors
        validate_entry_resources: Also validate each entry resource

    Returns:
        ValidationResult with combined issues
    """
    validator = FHIRValidator(strict=strict)
    result = validator.validate(bundle)

    if validate_entry_resources:
        # Get entries from bundle
        if isinstance(bundle, dict):
            entries = bundle.get("entry", [])
        else:
            entries = bundle.entry or []

        for i, entry in enumerate(entries):
            if isinstance(entry, dict):
                resource = entry.get("resource")
            else:
                resource = entry.resource

            if resource:
                entry_result = validator.validate(resource)
                for issue in entry_result.issues:
                    # Prefix path with entry index
                    if issue.path:
                        issue.path = f"entry[{i}].resource.{issue.path}"
                    else:
                        issue.path = f"entry[{i}].resource"
                result.merge(entry_result)

    return result


def check_required_fields(
    resource: Union[Resource, Dict[str, Any]],
    required_fields: List[str]
) -> ValidationResult:
    """
    Check that specific fields are present in a resource.

    Args:
        resource: Resource to check
        required_fields: List of field names to check

    Returns:
        ValidationResult
    """
    result = ValidationResult(is_valid=True)

    if isinstance(resource, dict):
        data = resource
        result.resource_type = resource.get("resourceType")
        result.resource_id = resource.get("id")
    else:
        data = resource.model_dump(exclude_none=True)
        result.resource_type = resource.resource_type
        result.resource_id = getattr(resource, "id", None)

    for field_name in required_fields:
        # Support nested field names with dot notation
        parts = field_name.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break

        if value is None:
            result.add_error(
                f"Required field '{field_name}' is missing",
                path=field_name,
                rule="required"
            )

    return result


def validate_references(
    bundle: Union[Bundle, Dict[str, Any]],
    check_internal: bool = True
) -> ValidationResult:
    """
    Validate that all references in a bundle can be resolved.

    Args:
        bundle: Bundle to validate
        check_internal: Verify references to resources within the bundle

    Returns:
        ValidationResult
    """
    result = ValidationResult(is_valid=True)
    result.resource_type = "Bundle"

    # Build index of resources in bundle
    resource_index: Set[str] = set()

    if isinstance(bundle, dict):
        entries = bundle.get("entry", [])
        result.resource_id = bundle.get("id")
    else:
        entries = bundle.entry or []
        result.resource_id = getattr(bundle, "id", None)

    for entry in entries:
        if isinstance(entry, dict):
            resource = entry.get("resource", {})
            res_type = resource.get("resourceType")
            res_id = resource.get("id")
        else:
            resource = entry.resource
            res_type = resource.resource_type if resource else None
            res_id = getattr(resource, "id", None) if resource else None

        if res_type and res_id:
            resource_index.add(f"{res_type}/{res_id}")

    # Check all references
    def check_ref(ref_value: str, path: str) -> None:
        # Skip external references
        if ref_value.startswith("http://") or ref_value.startswith("https://"):
            return
        if ref_value.startswith("urn:"):
            return
        if ref_value.startswith("#"):
            return

        # Check if reference exists in bundle
        if check_internal and ref_value not in resource_index:
            result.add_warning(
                f"Reference '{ref_value}' not found in bundle",
                path=path,
                rule="reference-resolution"
            )

    for i, entry in enumerate(entries):
        if isinstance(entry, dict):
            resource = entry.get("resource", {})
        else:
            resource = entry.resource
            if resource:
                resource = resource.model_dump(exclude_none=True)

        if resource:
            _find_references(resource, f"entry[{i}].resource", check_ref)

    return result


def _find_references(
    data: Any,
    path: str,
    callback: callable
) -> None:
    """Find all references in nested data structure."""
    if isinstance(data, dict):
        if "reference" in data and isinstance(data["reference"], str):
            callback(data["reference"], f"{path}.reference")
        for key, value in data.items():
            _find_references(value, f"{path}.{key}", callback)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _find_references(item, f"{path}[{i}]", callback)
