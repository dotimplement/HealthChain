"""
FHIR Resource Validation Example

Demonstrates validation helpers for ensuring FHIR resource correctness.
"""

import sys
sys.path.insert(0, "..")

from fhir_utils import (
    ResourceFactory,
    FHIRValidator,
    ValidationResult,
    validate_resource,
    validate_bundle,
    check_required_fields,
    validate_references,
)
from fhir_utils.bundle_tools import BundleBuilder


def basic_validation_example():
    """Basic resource validation."""
    print("=== Basic Resource Validation ===\n")

    # Create a valid patient
    patient = ResourceFactory.patient() \
        .with_name("Doe", given=["Jane"]) \
        .with_birth_date("1990-05-20") \
        .with_gender("female") \
        .build()

    result = validate_resource(patient)

    print(f"Patient validation: {'VALID' if result.is_valid else 'INVALID'}")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    print()


def validation_with_errors_example():
    """Validation with intentional errors."""
    print("=== Validation with Errors ===\n")

    # Create an invalid condition (missing required subject)
    invalid_condition_dict = {
        "resourceType": "Condition",
        "id": "invalid-condition",
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "73211009",
                "display": "Diabetes mellitus"
            }]
        }
        # Missing: subject reference (required)
    }

    result = validate_resource(invalid_condition_dict)

    print(f"Condition validation: {'VALID' if result.is_valid else 'INVALID'}")
    print(f"Errors: {result.error_count}")

    if result.errors:
        print("\nErrors found:")
        for error in result.errors:
            print(f"  - {error}")
    print()


def strict_validation_example():
    """Strict validation where warnings become errors."""
    print("=== Strict Validation Mode ===\n")

    # Create a patient without recommended fields
    minimal_patient = ResourceFactory.patient() \
        .with_id("minimal-patient") \
        .build()

    # Normal validation
    normal_result = validate_resource(minimal_patient, strict=False)
    print(f"Normal mode - Valid: {normal_result.is_valid}, Warnings: {normal_result.warning_count}")

    # Strict validation
    strict_result = validate_resource(minimal_patient, strict=True)
    print(f"Strict mode - Valid: {strict_result.is_valid}, Errors: {strict_result.error_count}")

    if strict_result.errors:
        print("\nStrict mode errors (from warnings):")
        for error in strict_result.errors:
            print(f"  - {error}")
    print()


def custom_validation_rules_example():
    """Using custom validation rules."""
    print("=== Custom Validation Rules ===\n")

    validator = FHIRValidator()

    # Add custom rule: patients must have at least one identifier
    def require_identifier(resource, result):
        identifiers = getattr(resource, "identifier", None)
        if not identifiers:
            result.add_error(
                "Patient must have at least one identifier",
                path="identifier",
                rule="require-identifier"
            )

    validator.add_custom_rule("Patient", require_identifier, "require-identifier")

    # Test with patient without identifier
    patient_no_id = ResourceFactory.patient() \
        .with_name("Smith", given=["John"]) \
        .with_gender("male") \
        .build()

    result1 = validator.validate(patient_no_id)
    print(f"Patient without identifier: {'VALID' if result1.is_valid else 'INVALID'}")
    for error in result1.errors:
        print(f"  - {error}")

    # Test with patient with identifier
    patient_with_id = ResourceFactory.patient() \
        .with_name("Smith", given=["John"]) \
        .with_gender("male") \
        .with_mrn("MRN123456") \
        .build()

    result2 = validator.validate(patient_with_id)
    print(f"Patient with identifier: {'VALID' if result2.is_valid else 'INVALID'}")
    print()


def bundle_validation_example():
    """Validate entire bundles including entries."""
    print("=== Bundle Validation ===\n")

    # Create a bundle with resources
    patient = ResourceFactory.patient() \
        .with_id("patient-bundle-test") \
        .with_name("Test", given=["User"]) \
        .build()

    condition = ResourceFactory.condition() \
        .for_patient("patient-bundle-test") \
        .with_snomed("73211009", "Diabetes mellitus") \
        .with_clinical_status("active") \
        .build()

    observation = ResourceFactory.observation() \
        .for_patient("patient-bundle-test") \
        .with_loinc("2339-0", "Glucose") \
        .with_value_quantity(100, "mg/dL") \
        .build()

    bundle = BundleBuilder() \
        .as_collection() \
        .add(patient) \
        .add(condition) \
        .add(observation) \
        .build()

    result = validate_bundle(bundle, validate_entry_resources=True)

    print(f"Bundle validation: {'VALID' if result.is_valid else 'INVALID'}")
    print(f"Total entries: {len(bundle.entry)}")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")

    if result.issues:
        print("\nAll issues:")
        for issue in result.issues:
            print(f"  [{issue.severity.value}] {issue.path}: {issue.message}")
    print()


def reference_validation_example():
    """Validate reference integrity in bundles."""
    print("=== Reference Validation ===\n")

    # Create bundle with valid references
    patient = ResourceFactory.patient() \
        .with_id("ref-test-patient") \
        .with_name("Reference", given=["Test"]) \
        .build()

    # Condition referencing existing patient
    valid_condition = ResourceFactory.condition() \
        .for_patient("ref-test-patient") \
        .with_snomed("38341003", "Hypertension") \
        .build()

    # Condition referencing non-existent patient
    invalid_condition = ResourceFactory.condition() \
        .for_patient("non-existent-patient") \
        .with_snomed("195967001", "Asthma") \
        .build()

    bundle = BundleBuilder() \
        .as_collection() \
        .add(patient) \
        .add(valid_condition) \
        .add(invalid_condition) \
        .build()

    result = validate_references(bundle, check_internal=True)

    print(f"Reference validation: {'VALID' if result.is_valid else 'INVALID'}")
    print(f"Warnings: {result.warning_count}")

    if result.warnings:
        print("\nUnresolved references:")
        for warning in result.warnings:
            print(f"  - {warning}")
    print()


def required_fields_example():
    """Check for specific required fields."""
    print("=== Required Fields Check ===\n")

    # Define custom required fields for your use case
    required_for_submission = [
        "id",
        "code",
        "subject",
        "clinicalStatus",
        "verificationStatus"
    ]

    # Complete condition
    complete_condition = ResourceFactory.condition() \
        .with_id("complete-condition") \
        .for_patient("patient-123") \
        .with_snomed("73211009", "Diabetes") \
        .with_clinical_status("active") \
        .with_verification_status("confirmed") \
        .build()

    result1 = check_required_fields(complete_condition, required_for_submission)
    print(f"Complete condition: {'VALID' if result1.is_valid else 'INVALID'}")

    # Incomplete condition (dict without all fields)
    incomplete_condition = {
        "resourceType": "Condition",
        "id": "incomplete-condition",
        "code": {"text": "Some condition"}
        # Missing: subject, clinicalStatus, verificationStatus
    }

    result2 = check_required_fields(incomplete_condition, required_for_submission)
    print(f"Incomplete condition: {'VALID' if result2.is_valid else 'INVALID'}")

    if result2.errors:
        print("\nMissing fields:")
        for error in result2.errors:
            print(f"  - {error.path}")
    print()


def validation_result_handling():
    """Working with validation results."""
    print("=== Working with Validation Results ===\n")

    patient = ResourceFactory.patient() \
        .with_id("result-demo") \
        .build()

    result = validate_resource(patient)

    # Convert to dictionary for logging/storage
    result_dict = result.to_dict()
    print("Result as dictionary:")
    print(f"  is_valid: {result_dict['is_valid']}")
    print(f"  error_count: {result_dict['error_count']}")
    print(f"  warning_count: {result_dict['warning_count']}")

    # String representation
    print("\nResult as string:")
    print(result)

    # Merge multiple results
    condition = ResourceFactory.condition() \
        .for_patient("result-demo") \
        .build()

    condition_result = validate_resource(condition)

    combined = ValidationResult(is_valid=True)
    combined.merge(result)
    combined.merge(condition_result)

    print(f"\nCombined validation: {combined.error_count} errors, {combined.warning_count} warnings")


def main():
    """Run all validation examples."""
    print("\n" + "=" * 60)
    print("FHIR Validation Examples")
    print("=" * 60 + "\n")

    basic_validation_example()
    validation_with_errors_example()
    strict_validation_example()
    custom_validation_rules_example()
    bundle_validation_example()
    reference_validation_example()
    required_fields_example()
    validation_result_handling()

    print("=" * 60)
    print("Validation examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
